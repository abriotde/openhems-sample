#!/bin/env python3
"""
Script used to test emhass by calling it as a docker.
"""


import logging
from pathlib import Path
import deferrable
import emhass.command_line as em
# import emhass.utils as em_utils
# https://emhass.readthedocs.io/en/latest/emhass.html

entity_path = "."
input_data_dict = {}
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# em.continual_publish(input_data_dict, entity_path, logger)

emhass_conf = {
	'config_path' : '/app/config_emhass.yaml',
	'data_path' : Path('/app/data'),
	'root_path' : Path('/app'),
}
secrets_path = '/app/secrets_emhass.yaml'
action_name = "dayahead-optim"
costfun = "profit"
runtimeparams = None
params = None
input_data_dict = em.set_input_data_dict(emhass_conf, costfun,
        params, runtimeparams, action_name, logger)

print("input_data_dict:",input_data_dict)
print("Opt:", input_data_dict['opt'].optim_conf)

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

# 'list_hp_periods': {
#    'period_hp_1': [{'start': '02:54'}, {'end': '15:24'}],
#    'period_hp_2': [{'start': '17:24'}, {'end': '20:24'}]
#  } 'load_cost_hp': 0.1907, 'load_cost_hc': 0.1419, 'prod_sell_price': 0.065

data = em.dayahead_forecast_optim(input_data_dict, logger) # pandas.core.frame.DataFrame

# print(list(data.columns))
# print(list(data.keys()))

# print(data)
for timestamp, row in data.iterrows():
	# type(timestamp) = pandas._libs.tslibs.timestamps.Timestamp
	for index, d in enumerate(deferables):
		print(timestamp, "=>", row['P_deferrable'+str(index)])
	# print(timestamp, "=>", row.P_deferrable1)
	print()
