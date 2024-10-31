#!/bin/env python3
"""
Script used to test emhass
* by calling it as a docker.
* by calling it source code
"""

import sys
import argparse
import logging
import json
from pathlib import Path
from importlib import util
import deferrable
from importlib.metadata import version
from packaging.version import Version

emhassModuleSpec = util.find_spec('emhass')
if emhassModuleSpec is not None and Version(version('emhass'))>Version('0.9.0'):
	print("module 'emhass' is installed on version ", version('emhass'))
else:
	print("module 'emhass' is not installed.")

parser = argparse.ArgumentParser()
parser.add_argument('--docker', action='store_true',
	help="Set this option if the script run"
	" in emhass docker davidusb/emhass-docker-standalone")
parser.add_argument('-e','--emhass_dir', type=str, default=None,
	help="The path to the directory where there is config_emhass.yaml, "
	"secrets_emhass.yaml and data dir.")
parser.add_argument('-r','--emhass_root', type=str, default=None,
	help="The path to the directory where there is emhass sources"
	" and emhass/data/associations.csv and emhass/data/config_defaults.json.")
args = parser.parse_args()

if args.docker:
	HOMEASSISTANT_EMHASS_DIR="/app"
else:
	# pip3 install numpy plotly skforecast setuptools requests bs4 pvlib pulp
	path_root = Path(__file__).parents[2]
	path_emhass = str(path_root)+'/lib/emhass/src/'
	sys.path.append(path_emhass)
	HOMEASSISTANT_EMHASS_DIR="/home/alberic/Documents/OpenHomeSystem/emhassenv"

# pylint: disable=wrong-import-position
# pylint: disable=import-error
# Import here because when use local sources, we need first to set this folder in the path
import emhass
import emhass.command_line as em
import emhass.utils as em_utils
# https://emhass.readthedocs.io/en/latest/emhass.html


logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
action_name = "dayahead-optim"
costfun = "profit"
runtimeparams = None

# entity_path = "."
# em.continual_publish(input_data_dict, entity_path, logger)

if args.docker:
	emhass_conf = {
		'config_path' : '/app/config_emhass.yaml',
		'data_path' : Path('/app/data'),
		'root_path' : Path('/app'),
	}
	secrets_path = '/app/secrets_emhass.yaml'
	params = None
else:
	emhass_conf = {
		'config_path' : HOMEASSISTANT_EMHASS_DIR+'/config_emhass.yaml',
		'data_path' : Path(HOMEASSISTANT_EMHASS_DIR+'/data'),
		'root_path' : Path(path_emhass+"/emhass"),
		'associations_path' : Path(path_emhass+'/emhass/data/associations.csv')
	}
	secrets_path = HOMEASSISTANT_EMHASS_DIR+'/secrets_emhass.yaml'
	# print("emhass_conf:",emhass_conf)
	config = em_utils.build_config(emhass_conf, logger,\
		Path(path_emhass+'/emhass/data/config_defaults.json'),\
		None,None )
	# print("config:",config)
	params_secrets = {}
	emhass_conf, built_secrets = em_utils.build_secrets(\
		emhass_conf, logger, secrets_path=secrets_path)
	params_secrets.update(built_secrets)
	# print("paramsSecrets", built_secrets, secrets_path)
	params = em_utils.build_params(emhass_conf, params_secrets, config, logger)
	params = json.dumps(params)

# print("params:",params)
input_data_dict = em.set_input_data_dict(emhass_conf, costfun,
        params, runtimeparams, action_name, logger)
# print("input_data_dict:",input_data_dict)

if input_data_dict:
	# print("Opt:", input_data_dict)
#	print("Opt:", input_data_dict['opt'].optim_conf)

	# Change deferables because in OpenHEMS, it can change from day to day
	deferables = [
		deferrable.Deferrable(1000, 3),
		deferrable.Deferrable(300, 2),
		deferrable.Deferrable(1500, 5)
	]
	optim_conf = input_data_dict['opt'].optim_conf
	optim_conf['num_def_loads'] = len(deferables)
	optim_conf['P_deferrable_nom'] = [d.power for d in deferables]
	optim_conf['def_total_hours'] = [d.duration for d in deferables]
	optim_conf['def_start_timestep'] = [d.start_timestep for d in deferables]
	optim_conf['def_end_timestep'] = [d.end_timestep for d in deferables]
	optim_conf['set_def_constant'] = [d.constant for d in deferables]
	optim_conf['def_start_penalty'] = [d.start_penalty for d in deferables]
	optim_conf['treat_def_as_semi_cont'] = [d.as_semi_cont for d in deferables]

	optim_conf['number_of_deferrable_loads'] = optim_conf['num_def_loads']
	optim_conf['nominal_power_of_deferrable_loads'] = optim_conf['P_deferrable_nom']
	optim_conf['operating_hours_of_each_deferrable_load'] = optim_conf['def_total_hours']
	optim_conf['treat_deferrable_load_as_semi_cont'] = optim_conf['treat_def_as_semi_cont']
	optim_conf['set_deferrable_load_single_constant'] = optim_conf['set_def_constant']
	optim_conf['set_deferrable_startup_penalty'] = optim_conf['def_start_penalty']
	optim_conf['end_timesteps_of_each_deferrable_load'] = optim_conf['def_end_timestep']
	optim_conf['start_timesteps_of_each_deferrable_load'] = optim_conf['def_start_timestep']

#	print("New opt:", input_data_dict['opt'].optim_conf)

	# 'list_hp_periods': {
	#    'period_hp_1': [{'start': '02:54'}, {'end': '15:24'}],
	#    'period_hp_2': [{'start': '17:24'}, {'end': '20:24'}]
	#  } 'load_cost_hp': 0.1907, 'load_cost_hc': 0.1419, 'prod_sell_price': 0.065

	data = em.dayahead_forecast_optim(input_data_dict, logger) # pandas.core.frame.DataFrame

	# print(list(data.columns))
	# print(list(data.keys()))

	print(data)

	for timestamp, row in data.iterrows():
		# type(timestamp) = pandas._libs.tslibs.timestamps.Timestamp
		for index, d in enumerate(deferables):
			print(timestamp, "=>", row['P_deferrable'+str(index)])
		# print(timestamp, "=>", row.P_deferrable1)
		print()
else:
	print("Error in configuration")
