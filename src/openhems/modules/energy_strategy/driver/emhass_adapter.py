#!/bin/env python3
"""
Module to use [EMHASS](https://github.com/davidusb-geek/emhass) on OpenHEMS
"""

import os
import logging
import json
import sys
import dataclasses
from pathlib import Path
import importlib
from importlib.metadata import version
import yaml
from packaging.version import Version

PATH_ROOT = Path(__file__).parents[5]
PATH_EMHASS = PATH_ROOT / 'lib/emhass/src/'
emhassModuleSpec = importlib.util.find_spec('emhass')
if emhassModuleSpec is not None: # TODO (Error codecov pipeline) and Version(version('emhass'))>Version('0.9.0'):
	print("module 'emhass' is installed on version ", version('emhass'))
else:
	print("module 'emhass' is not installed, Add it from source (",PATH_EMHASS,").")
	sys.path.append(str(PATH_EMHASS))

# pylint: disable=wrong-import-position, import-error, no-name-in-module
# Import here because when use local sources, we need first to set this folder in the path
# import emhass
import emhass.command_line as em
import emhass.utils as em_utils


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

class EmhassAdapter:
	"""
	Class to use easily EMHASS on OpenHEMS.
	"""
	def __init__(self, configPath:Path, dataPath:Path,
			rootPath:Path , associationsPath:Path = None):
		self.logger = logging.getLogger(__name__)
		if associationsPath is None:
			associationsPath = rootPath / 'data/associations.csv'
		self.logger.debug("EmhassAdapter(%s, %s, %s, %s)",
			configPath, dataPath, rootPath , associationsPath)
		# self.configPath = configPath
		# self.dataPath = dataPath
		self.rootPath = rootPath
		# self.associationsPath = associationsPath
		self._emhassConf = {
			'config_path' : str(configPath / 'config_emhass.yaml'),
			'data_path' : dataPath,
			'root_path' : rootPath,
			'associations_path' : associationsPath
		}
		self._secretsPath = configPath / 'secrets_emhass.yaml'
		self.deferables = []
		self.deferables = [] # List[Deferrable]
		self._params = {}
		self.initialyzeHEMASS()

	def initialyzeHEMASS(self):
		"""
		Initialyze HEMASS after defining paramters in __init__()
		"""
		# print("emhass_conf:",self._emhassConf)
		config = em_utils.build_config(self._emhassConf, self.logger,\
			self.rootPath / 'data/config_defaults.json', None, None)
		# print("config:",config)
		paramsSecrets = {}
		self._emhassConf, builtSecrets = em_utils.build_secrets(\
			self._emhassConf, self.logger, secrets_path=str(self._secretsPath))
		paramsSecrets.update(builtSecrets)
		self._params = em_utils.build_params(self._emhassConf, paramsSecrets, config, self.logger)

	def performOptim(self, actionName:str = "dayahead-optim", costfun:str = "profit"):
		"""
		:return:  # pandas.core.frame.DataFrame
		"""
		self.logger.info("EmhassAdapter.performOptim(%s, %s) for %s",
			actionName, costfun, str(self))
		runtimeparams = None
		params = self._params if isinstance(self._params, str) else json.dumps(self._params)
		# print("params:",params)
		inputDataDict = em.set_input_data_dict(self._emhassConf, costfun,
				params, runtimeparams, actionName, self.logger)

		optimConf = inputDataDict['opt'].optim_conf
		optimConf['num_def_loads'] = len(self.deferables)
		optimConf['P_deferrable_nom'] = [d.power for d in self.deferables]
		optimConf['def_total_hours'] = [d.duration for d in self.deferables]
		optimConf['def_start_timestep'] = [d.startTimestep for d in self.deferables]
		optimConf['def_end_timestep'] = [d.endTimestep for d in self.deferables]
		optimConf['set_def_constant'] = [d.constant for d in self.deferables]
		optimConf['def_start_penalty'] = [d.startPenalty for d in self.deferables]
		optimConf['treat_def_as_semi_cont'] = [d.asSemiCont for d in self.deferables]

		optimConf['number_of_deferrable_loads'] = optimConf['num_def_loads']
		optimConf['nominal_power_of_deferrable_loads'] = optimConf['P_deferrable_nom']
		optimConf['operating_hours_of_each_deferrable_load'] = optimConf['def_total_hours']
		optimConf['treat_deferrable_load_as_semi_cont'] = optimConf['treat_def_as_semi_cont']
		optimConf['set_deferrable_load_single_constant'] = optimConf['set_def_constant']
		optimConf['set_deferrable_startup_penalty'] = optimConf['def_start_penalty']
		optimConf['end_timesteps_of_each_deferrable_load'] = optimConf['def_end_timestep']
		optimConf['start_timesteps_of_each_deferrable_load'] = optimConf['def_start_timestep']
		# print("New opt:", inputDataDict['opt'].optim_conf)

		# 'list_hp_periods': {
		#    'period_hp_1': [{'start': '02:54'}, {'end': '15:24'}],
		#    'period_hp_2': [{'start': '17:24'}, {'end': '20:24'}]
		#  } 'load_cost_hp': 0.1907, 'load_cost_hc': 0.1419, 'prod_sell_price': 0.065

		emhassData = em.dayahead_forecast_optim(inputDataDict, self.logger)
		return emhassData

	@staticmethod
	def generateConfigFromOpenHEMS(path:Path):
		"""
		Generate configurations files from OpenHEMS configuration.
		Avoid to maintain multiple files with duplicated informations
		 (So possibly inconsistense and difficult error to resolv)
		"""
		openHEMSPath = path / "openhems.yaml"
		emhassPath = path / "config_emhass.yaml"
		emhassSecretsPath = path / "secrets_emhass.yaml"
		with open(openHEMSPath, 'r', encoding="utf-8") as openHEMSFile:
			openhemsConf = yaml.load(openHEMSFile, Loader=yaml.FullLoader)
			apiConf = openhemsConf["api"]
			url = apiConf["url"]
			token = apiConf["long_lived_token"]
			url = apiConf["url"]
			latitude = openhemsConf["latitude"]
			longitude = openhemsConf["longitude"]
			altitude = openhemsConf["altitude"]
			tz = openhemsConf["time_zone"]
			with open(emhassSecretsPath, 'w', encoding="utf-8") as emhassSecretsFile:
				emhassSecretsFile.write(f"""
# Auto-generated file by openhems.EmhassAdapter.generateConfigFromOpenHEMS()

hass_url: {url}
long_lived_token: {token}
time_zone: {tz}
lat: {latitude}
lon: {longitude}
alt: {altitude}
""")
			with open(emhassPath, 'w', encoding="utf-8") as emhassFile:
				emhassFile.write("")

	@staticmethod
	def createForOpenHEMS():
		"""
		Create EmhassAdapter with parameters for standard OpenHEMS installations
		"""
		configPath = PATH_ROOT / "config"
		# self.generateConfigFromOpenHEMS()
		dataPath = Path("/tmp/emhass_data")
		if not os.path.exists(dataPath):
			os.mkdir(dataPath)
		rootPath = PATH_EMHASS / "emhass"
		return EmhassAdapter(configPath, dataPath, rootPath)

	@staticmethod
	def createForDocker():
		"""
		Create EmhassAdapter with parameters
		 for standard Docker installation (davidusb/emhass-docker-standalone)
		"""
		rootPath = Path("/app")
		dataPath = rootPath / "data"
		return EmhassAdapter(rootPath, dataPath, rootPath)

if __name__ == "__main__":
	emhass = EmhassAdapter.createForOpenHEMS()
	emhass.deferables = [
		Deferrable(1000, 3),
		Deferrable(300, 2),
		Deferrable(1500, 5)
	]
	data = emhass.performOptim()
	print(data)
