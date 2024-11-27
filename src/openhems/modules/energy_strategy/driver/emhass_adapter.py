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
# from importlib.metadata import version
import yaml
import jinja2
from jinja2 import Environment, FileSystemLoader
# from packaging.version import Version
PATH_ROOT = Path(__file__).parents[5]
PATH_EMHASS = PATH_ROOT / 'lib/emhass/src/'
emhassModuleSpec = importlib.util.find_spec('emhass')
logger = logging.getLogger(__name__)

# pylint: disable=condition-evals-to-constant
if False and emhassModuleSpec is not None:
	# and Version(version('emhass'))>Version('0.9.0'):
	# As we can't get EMHASS version, we can't be sure, it's ok
	# TODO (Error codecov pipeline, fail import package metadata)
	print("module 'emhass' is installed on version ") # , version('emhass'))
else:
	print(os.listdir(PATH_EMHASS))
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
	duration: float # Duration in hours? (In emhass granularity)
	node:str = None
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
		configDefaultJson = self.rootPath / 'data/config_defaults.json'
		emhassConfig = self._emhassConf['config_path']
		self.logger.info("Load config_default.json : %s, emhass_config.yaml : %s",
			configDefaultJson, emhassConfig)
		config = em_utils.build_config(self._emhassConf, self.logger,\
			configDefaultJson, legacy_config_path=emhassConfig)
		# print("config:",config)
		self.logger.info("Load emhass_secrets.yaml : %s", self._secretsPath)
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

		assert not isinstance(inputDataDict, bool)
		if isinstance(inputDataDict, bool):
			return False

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
	def generateSecretConfig(configurator, emhassSecretsPath:Path):
		"""
		Generate configurations files from OpenHEMS configuration.
		Avoid to maintain multiple files with duplicated informations
		 (So possibly inconsistense and difficult error to resolv)
		"""
		url = configurator.get("api.url")
		token = configurator.get("api.long_lived_token")
		tz = configurator.get("timeZone")
		latitude = configurator.get("latitude")
		longitude = configurator.get("longitude")
		altitude = configurator.get("altitude")
		with emhassSecretsPath.open('w', encoding="utf-8") as emhassSecretsFile:
			logger.info("Write EMHASS secret configuration on '%s'", emhassSecretsPath)
			emhassSecretsFile.write(f"""
# Auto-generated file by openhems.EmhassAdapter.generateSecretConfig()

hass_url: {url}
long_lived_token: {token}
time_zone: {tz}
lat: {latitude}
lon: {longitude}
alt: {altitude}
""")

	@staticmethod
	def haTemplateVar(varName):
		"""
		Return Home-Assistant dynamic var value
		 used for formule in YAML Home-Assistant file configuration.
		"""
		return '(states("'+varName+'") | float(0))'

	@staticmethod
	def generateHomeAssistantTemplateConfig(configurator, network, templateYamlPath:Path):
		"""
		Return Home-Assistant template.yaml file
		 fill according to openhems.yaml config.
		"""
		# TODO: compute varPV && varLoad
		varPV = EmhassAdapter.haTemplateVar('sensor.lixee_zlinky_tic_puissance_apparente')
			+" - "+ EmhassAdapter.haTemplateVar('sensor.lixee_zlinky_tic_puissance_apparente')
		varLoad = EmhassAdapter.haTemplateVar('sensor.lixee_zlinky_tic_puissance_apparente')
			+" - "+ EmhassAdapter.haTemplateVar('sensor.lixee_zlinky_tic_puissance_apparente')
		with templateYamlPath.open('w', encoding="utf-8") as file:
			logger.info("Write home-Assistant template configuration on '%s'", templateYamlPath)
			file.write(f"""
# Auto-generated file by openhems.EmhassAdapter.generateHomeAssistantTemplateConfig()
  - sensor:
    - unique_id: sensor.emhass_photovoltaic_power_produced
      name: "EMHASS - Photovoltaic power-produced"
      state: '{{ {varPV} }}'
      unit_of_measurement: "Watt"
      device_class: energy
  - sensor:
    - unique_id: sensor.emhass_household_power_consumption
      name: "EMHASS - Household power consumption"
      state: '{{ {varLoad} }}'
      unit_of_measurement: "Watt"
      device_class: energy
""")

	@staticmethod
	def getEmhassDatas(configurator, network):
		"""
		"""
		datas = configurator.get("emhass", None, True)
		# P_from_grid_max / P_to_grid_max
		maxPower = network.getMaxPower()
		datas['P_from_grid_max'] = network.getMaxPower("publicpowergrid")
		datas['P_to_grid_max'] = network.getMinPower("publicpowergrid")
		setUseBattery = False
		Pd_max = 0
		eta_disch = 0
		for elem in network.getAll("solarpanel"):
			setUseBattery = True
			Pd_max += elem.
		datas['set_use_battery'] = setUseBattery
		datas['Pd_max'] = Pd_max
		datas['Pc_max'] = Pc_max
		datas['eta_disch'] = eta_disch
		datas['eta_ch'] = setUseBattery
		datas['Enom'] = setUseBattery
		datas['SOCmin'] = SOCmin
		datas['SOCmax'] = SOCmax
		datas['SOCtarget'] = 
		print("Datas:",datas)
		return datas

	@staticmethod
	def generateYamlConfig(configurator, network, emhassConfigPath:Path):
		templateDirPath = str(Path(__file__).parents[0] / "data/")
		templateName = "config_emhass.jinja2.yaml"
		environment = Environment(loader=FileSystemLoader(templateDirPath))
		datas = EmhassAdapter.getEmhassDatas(configurator, network)
		try:
			template = environment.get_template(templateName)
			content = template.render(
				datas,
				max_score=100,
				test_name="toto"
			)
			with emhassConfigPath.open('w', encoding="utf-8") as emhassFile:
				logger.info("Write EMHASS configuration on '%s'", emhassConfigPath)
				emhassFile.write("# Auto-generated file by openhems.EmhassAdapter.generateYamlConfig()")
				emhassFile.write(content)
				return True
		except jinja2.exceptions.TemplateNotFound:
			logger.error(
				"Fail write EMHASS configuration on '%s : TemplateNotFound(%s/%s)",
				emhassConfigPath, templateDirPath, templateName
			)
		exit(1)
		return False

	@staticmethod
	def createFromOpenHEMS(configuration=None, network=None):
		"""
		Create EmhassAdapter with parameters for standard OpenHEMS installations
		"""
		configPath = PATH_ROOT / "config"
		if configuration is not None:
			# EmhassAdapter.generateSecretConfig(
			# 	configuration,
			# 	configPath / "secrets_emhass.yaml"
			# )
			if network is not None:
				EmhassAdapter.generateYamlConfig(
					configuration, network,
					configPath / "config_emhass.yaml"
				)
				EmhassAdapter.generateHomeAssistantTemplateConfig(
					configuration, network,
					configPath / "template.yaml"
				)
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
	sys.path.append(str(PATH_ROOT/"src"))
	from openhems.modules.util.configuration_manager import ConfigurationManager
	configurator = ConfigurationManager(logger)
	emhass = EmhassAdapter.createFromOpenHEMS(configurator)
	emhass.deferables = [
		Deferrable(1000, 3),
		Deferrable(300, 2),
		Deferrable(1500, 5)
	]
	data = emhass.performOptim()
	print(data)
