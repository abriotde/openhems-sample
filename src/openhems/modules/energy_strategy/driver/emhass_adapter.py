#!/bin/env python3
"""
Module to use [EMHASS](https://github.com/davidusb-geek/emhass) on OpenHEMS
"""

import os
import logging
import json
import sys
import math
from pathlib import Path
import importlib
# from importlib.metadata import version
import jinja2
from jinja2 import Environment, FileSystemLoader
from openhems.modules.util.configuration_manager import ConfigurationException
# from packaging.version import Version
PATH_ROOT = Path(__file__).parents[3]
PATH_EMHASS = PATH_ROOT / 'emhass/src/'
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


class Deferrable:
	"""
	Custom class to simplify emhass module live modifications.
	"""
	power: float # Nominal power
	_duration: float # Duration in hours? (In emhass granularity)
	node = None
	startTimestep = 0
	endTimestep = 0
	constant = False
	startPenalty: float = 0.0
	asSemiCont: bool = True

	def __init__(self, power:float, duration:float, node=None):
		self.power = power
		self._duration = duration
		self.node = node

	def getDuration(self):
		"""
		return: duration in seconds
		"""
		return self._duration
	def getDurationInHours(self):
		"""
		Return duration in Emhass prevision granularity
		"""
		# TODO granularity can be less or more than hour...
		return math.ceil(self._duration / 3600)
	def setDuration(self, duration):
		"""
		param: duration: in seconds
		"""
		self._duration = duration

class EmhassAdapter:
	"""
	Class to use easily EMHASS on OpenHEMS.
	"""
	def __init__(self, configPath:Path, dataPath:Path,
			rootPath:Path , associationsPath:Path = None):
		self.logger = logging.getLogger(__name__)
		if associationsPath is None:
			associationsPath = rootPath / 'data/associations.csv'
		if not os.path.exists(associationsPath):
			self.logger.error("Can't find associations file on '%s'", associationsPath)
			raise ConfigurationException(f"Can't find associations file on '{associationsPath}'")
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
		self.logger.debug("EmhassAdapter.performOptim(%s, %s) for %s",
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
		optimConf['def_total_hours'] = [d.getDurationInHours() for d in self.deferables]
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
	def generateSecretConfig(configuration, emhassSecretsPath:Path):
		"""
		Generate configurations files from OpenHEMS configuration.
		Avoid to maintain multiple files with duplicated informations
		 (So possibly inconsistense and difficult error to resolv)
		"""
		url = configuration.get("api.url")
		if url.endswith("/api"):
			url = url[:-3]
		token = configuration.get("api.long_lived_token")
		tz = configuration.get("localization.timeZone")
		latitude = configuration.get("localization.latitude")
		longitude = configuration.get("localization.longitude")
		altitude = configuration.get("localization.altitude")
		with emhassSecretsPath.open('w', encoding="utf-8") as emhassSecretsFile:
			logger.info("Write EMHASS secret configuration on '%s'", emhassSecretsPath)
			emhassSecretsFile.write(f"""
# Auto-generated file by openhems.EmhassAdapter.generateSecretConfig()

hass_url: {url}
long_lived_token: {token}
time_zone: {tz}
Latitude: {latitude}
Longitude: {longitude}
Altitude: {altitude}
""")

	@staticmethod
	def generateHomeAssistantTemplateConfig(network, templateYamlPath:Path):
		"""
		Return Home-Assistant template.yaml file
		 fill according to openhems.yaml config.
		"""
		inout = ['(states("'+elem.currentPower.nameid+'") | float(0))'
			for elem in network.getAll("inout")]
		out = ['(states("'+elem.currentPower.nameid+'") | float(0))'
			for elem in network.getAll("out")]
		solarpanel = ['(states("'+elem.currentPower.nameid+'") | float(0))'
			for elem in network.getAll("solarpanel")]
		if len(inout)==0 or len(out)==0 or len(solarpanel)==0:
			logger.error("Emhass optimization need %s configuration.",
				"inout" if len(inout)==0 else
				"out" if len(out)==0 else
				"solarpanel" if len(solarpanel)==0 else "")
			return False
		varLoad = " + ".join(inout) + " - "+ " - ".join(out)
		varPV = " + ".join(solarpanel)
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
			return True
		return False

	@staticmethod
	def getYamlList(elems, caller=None, indent="  "):
		"""
		Convert a Python list to a YAML one
		"""
		if caller is not None:
			elems = [str(caller(elem).getValue()) for elem in elems]
		if len(elems)==0:
			return ""
		init = "\n"+indent+"- "
		return init+(init.join(elems))

	@staticmethod
	def getYamlConfOffpeakHours(network):
		"""
		Return YAML configuration for Emhass off-peak hours.
		"""
		datas = {}
		# The peak-price/offpeak-price is approximative
		# isn't exact because we can have many different price during the day.
		for elem in network.getAll("publicpowergrid"):
			contract = elem.getContract()
			ranges = contract.getOffPeakHoursRanges()
			peakPrice = contract.getPeakPrice()
			listHpPeriods = ""
			i = 1
			for r in ranges:
				start = repr(r[0])
				end = repr(r[1])
				listHpPeriods += f"""\n  - period_hp_{i}:
    - start: '{start}'
    - end: '{end}'
"""
				i+=1
			if listHpPeriods == "":
				listHpPeriods = "[]"
			datas["list_hp_periods"] = listHpPeriods
			datas["load_cost_hp"] = peakPrice
			datas["load_cost_hc"] = contract.getOffPeakPrice()
		return datas

	@staticmethod
	def getYamlConfBattery(network):
		"""
		Extract usefull informations from openhems.yaml configuration
		 for configuring EMHASS Battery fields
		Return: Dict of varname=>String to felle configuration file.
		"""
		datas = {}
		# Feel battery fields
		maxPowerOut = 0
		maxPowerIn = 0
		efficiencyIn = 0
		efficiencyOut = 0
		capacity = 0
		lowLevel = 0
		highLevel = 0
		targetLevel = 0
		for elem in network.getAll("battery"):
			maxPowerOut += elem.getMaxPower()
			maxPowerIn += elem.getMinPower()
			capa += elem.capacity
			efficiencyIn += elem.efficiencyIn * capa
			efficiencyOut += elem.efficiencyOut * capa
			capacity += capa
			lowLevel += elem.lowLevel * capa
			highLevel += elem.highLevel * capa
			targetLevel += elem.targetLevel * capa
		datas['set_use_battery'] = maxPowerOut>0 and capacity>0
		if capacity>0:
			datas['Pd_max'] = maxPowerOut
			datas['Pc_max'] = maxPowerIn
			datas['eta_disch'] = efficiencyIn / capacity
			datas['eta_ch'] = efficiencyOut / capacity
			datas['Enom'] = capacity
			datas['SOCmin'] = lowLevel / capacity
			datas['SOCmax'] = highLevel / capacity
			datas['SOCtarget'] = targetLevel / capacity
		return datas

	@staticmethod
	def getEmhassDatas(configurationEmhass, network, useTemplateVar=False):
		"""
		Extract usefull informations from openhems.yaml configuration
		 for configuring EMHASS
		Return: Dict of varname=>String to felle configuration file.
		"""
		datas = configurationEmhass
		# P_from_grid_max / P_to_grid_max
		datas['P_from_grid_max'] = network.getMaxPower("publicpowergrid")
		datas['P_to_grid_max'] = network.getMinPower("publicpowergrid")
		elems = network.getAll("inout")
		zeroRelacementVars = [
			'sensor.emhass_photovoltaic_power_produced',
			'sensor.emhass_household_power_consumption'
		] + [elem.currentPower.nameid for elem in elems]
		datas['var_replace_zero'] = EmhassAdapter.getYamlList(zeroRelacementVars)
		elems = network.getAll("solarpanel")
		interpretVars = [
			'sensor.emhass_photovoltaic_power_produced'
		] + [elem.currentPower.nameid for elem in elems]
		datas['var_interp'] = EmhassAdapter.getYamlList(interpretVars)

		# Feel solarpanel fields
		elems = network.getAll("solarpanel")
		datas['module_model'] = EmhassAdapter.getYamlList(elems, lambda x:
			x.moduleModel)
		datas['inverter_model'] = EmhassAdapter.getYamlList(elems, lambda x:
			x.inverterModel)
		datas['surface_tilt'] = EmhassAdapter.getYamlList(elems, lambda x:
			x.tilt)
		datas['surface_azimuth'] = EmhassAdapter.getYamlList(elems, lambda x:
			x.azimuth)
		datas['modules_per_string'] = EmhassAdapter.getYamlList(elems, lambda x:
			x.modulesPerString)
		datas['strings_per_inverter'] = EmhassAdapter.getYamlList(elems, lambda x:
			x.stringsPerInverter)
		if useTemplateVar:
			varPV = "sensor.emhass_photovoltaic_power_produced"
			varLoad = "sensor.emhass_household_power_consumption"
		else:
			for elem in network.getAll("solarpanel"):
				varPV = elem.currentPower.nameid
			for elem in network.getAll("inout"):
				varLoad = elem.currentPower.nameid
		datas['emhass_photovoltaic_power_produced'] =varPV
		datas['emhass_household_power_consumption'] =varLoad

		datas = datas \
			|EmhassAdapter.getYamlConfBattery(network) \
			|EmhassAdapter.getYamlConfOffpeakHours(network)
		# print("Datas:",datas)
		return datas

	@staticmethod
	def generateYamlConfig(configurationEmhass, network, emhassConfigPath:Path, useTemplateVar=False):
		"""
		Generate Emhass YAML config file : config_emhass.yaml from openhems.yaml
		"""
		templateDirPath = str(Path(__file__).parents[0] / "data/")
		templateName = "config_emhass.jinja2.yaml"
		environment = Environment(loader=FileSystemLoader(templateDirPath))
		datas = EmhassAdapter.getEmhassDatas(configurationEmhass, network, useTemplateVar)
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
		return False

	@staticmethod
	def createFromOpenHEMS(configurationGlobal=None, configurationEmhass:dict=None, network=None):
		"""
		Create EmhassAdapter with parameters for standard OpenHEMS installations
		"""
		print(f"createFromOpenHEMS({configurationGlobal}, {configurationEmhass})")
		dataPath = Path("/tmp/emhass_data")
		if not os.path.exists(dataPath):
			os.mkdir(dataPath)
		if configurationGlobal is not None:
			EmhassAdapter.generateSecretConfig(
				configurationGlobal,
				dataPath / "secrets_emhass.yaml"
			)
		else:
			logger.warning(
				"Can't generate EMHASS secrets due to missing configuration params."
			)
		if configurationEmhass is not None:
			if network is not None:
				useTemplateVar=False # It would be better set to True
				# but need to update Home-Assistant configurations... too complex.
				if useTemplateVar:
					EmhassAdapter.generateHomeAssistantTemplateConfig(
						network,
						dataPath / "template.yaml"
					)
				EmhassAdapter.generateYamlConfig(
					configurationEmhass, network,
					dataPath / "config_emhass.yaml",
					useTemplateVar=useTemplateVar
				)
			else:
				logger.warning(
					"Can't generate EMHASS configuration due to missing network param."
				)
		else:
			logger.warning(
				"Can't generate EMHASS secrets due to missing EMHASS configuration params."
			)
		rootPath = PATH_EMHASS / "emhass"
		return EmhassAdapter(dataPath, dataPath, rootPath)

	@staticmethod
	def createForDocker():
		"""
		Create EmhassAdapter with parameters
		 for standard Docker installation (davidusb/emhass-docker-standalone)
		"""
		rootPath = Path("/app")
		dataPath = rootPath / "data"
		return EmhassAdapter(rootPath, dataPath, rootPath)
