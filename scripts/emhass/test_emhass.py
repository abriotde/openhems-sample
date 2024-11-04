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
	print("In docker mode")
	HOMEASSISTANT_EMHASS_DIR="/app"
	CONFIG_DIR="/app"
else:
	PATH_ROOT = Path(__file__).parents[2]
	sys.path.append(str(PATH_ROOT / 'src'))
	PATH_EMHASS = str(PATH_ROOT / 'lib/emhass/src')
	sys.path.append(PATH_EMHASS)
	# print("PATH:", sys.path)
	CONFIG_DIR = str(PATH_ROOT / 'config')
	HOMEASSISTANT_EMHASS_DIR="/home/alberic/Documents/OpenHomeSystem/emhassenv"

# pylint: disable=wrong-import-position
# pylint: disable=no-name-in-module
# Import here because when use local sources, we need first to set this folder in the path
from emhass import command_line as em
from emhass import utils as em_utils
# https://emhass.readthedocs.io/en/latest/emhass.html


logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
ACTION_NAME = "dayahead-optim"
COSTFUN = "profit"
RUNTIMEPARAMS = None

# entity_path = "."
# em.continual_publish(input_data_dict, entity_path, logger)

if args.docker:
	emhass_conf = {
		'config_path' : '/app/config_emhass.yaml',
		'data_path' : Path('/app/data'),
		'root_path' : Path('/app'),
	}
	SECRETS_PATH = '/app/secrets_emhass.yaml'
	PARAMS = None
	import dataclasses
	# pylint: disable=duplicate-code
	# No choice to duplicate code as docker as no access to OpenHEMS code.
	@dataclasses.dataclass
	class Deferrable:
		"""
		Custom class to simplify emhass module live modifications.
		"""
		power: float # Nominal power
		duration: int # Duration in seconds
		startTimestep = 0
		endTimestep = 0
		constant = False
		startPenalty: float = 0.0
		asSemiCont: bool = True
else:
	from openhems.modules.energy_strategy.driver.emhass_adapter import Deferrable
	emhass_conf = {
		'config_path' : CONFIG_DIR+'/config_emhass.yaml',
		'data_path' : Path(HOMEASSISTANT_EMHASS_DIR+'/data'),
		'root_path' : Path(PATH_EMHASS+"/emhass"),
		'associations_path' : Path(PATH_EMHASS+'/emhass/data/associations.csv')
	}
	SECRETS_PATH = CONFIG_DIR+'/secrets_emhass.yaml'
	# print("emhass_conf:",emhass_conf)
	retrieve_json = Path(PATH_EMHASS+'/emhass/data/config_defaults.json')
	# print("retrieve_json:",retrieve_json)
	config = em_utils.build_config(emhass_conf, logger, retrieve_json, \
		legacy_config_path=emhass_conf['config_path'])
	# print("config:",config)
	paramsSecrets = {}
	emhass_conf, built_secrets = em_utils.build_secrets(\
		emhass_conf, logger, secrets_path=SECRETS_PATH)
	paramsSecrets.update(built_secrets)
	# print("PARAMSSecrets", built_secrets, SECRETS_PATH)
	PARAMS = em_utils.build_params(emhass_conf, paramsSecrets, config, logger)
	PARAMS = json.dumps(PARAMS)

print("PARAMS:",PARAMS)
print("RUNTIMEPARAMS:",RUNTIMEPARAMS)
print("emhass_conf:",emhass_conf)
input_data_dict = em.set_input_data_dict(emhass_conf, COSTFUN,
        PARAMS, RUNTIMEPARAMS, ACTION_NAME, logger)
print("input_data_dict:",input_data_dict)

if input_data_dict:
	# print("Opt:", input_data_dict)
#	print("Opt:", input_data_dict['opt'].optim_conf)

	# Change deferables because in OpenHEMS, it can change from day to day
	deferables = [
		Deferrable(1000, 3),
		Deferrable(300, 2),
		Deferrable(1500, 5)
	]
	optim_conf = input_data_dict['opt'].optim_conf
	optim_conf['num_def_loads'] = len(deferables)
	optim_conf['P_deferrable_nom'] = [d.power for d in deferables]
	optim_conf['def_total_hours'] = [d.duration for d in deferables]
	optim_conf['def_start_timestep'] = [d.startTimestep for d in deferables]
	optim_conf['def_end_timestep'] = [d.endTimestep for d in deferables]
	optim_conf['set_def_constant'] = [d.constant for d in deferables]
	optim_conf['def_start_penalty'] = [d.startPenalty for d in deferables]
	optim_conf['treat_def_as_semi_cont'] = [d.asSemiCont for d in deferables]

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
