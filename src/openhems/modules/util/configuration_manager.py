"""
Usefull generic configuration manager.
Let allow get configuration by key, init with a default value.
"""

import os
import yaml
from pathlib import Path

class ConfigurationException(Exception):
	"""
	Custom Configuration exception.
	"""
	def __init__(self, message, defaultValue):
		self.message = message
		self.defaultValue = defaultValue

class Singleton(type):
	_instances = {}
	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
		    cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
		return cls._instances[cls]

class ConfigurationManager(metaclass=Singleton):
	"""
	Usefull generic configuration manager.
	Let allow get configuration by key.
	1. init with a default value.
	2. Overload with user defined configuration value (If key defined as default)
	3. get the value by key/value dict
	"""
	_instance = None
	def __init__(self, logger, defaultPath=None):
		self.logger = logger
		if defaultPath  is None:
			ROOT_PATH = Path(__file__).parents[4]
			defaultPath = ROOT_PATH / "data/openhems_default.yaml"
		elif defaultPath is str:
			defaultPath = Path(defaultPath)
		self._conf = {}
		self.add_yaml_config(defaultPath, True)

	def _load(self, dict_config, init=False, prekey=''):
		"""
		Add configuration from recursive dictionary.
		"""
		# print("_load(",dict_config,")")
		for key, value in dict_config.items():
			# print("> ",key," => ", value)
			if isinstance(value, dict):
				self._load(value, init, prekey+key+'.')
			else:
				k = prekey+key
				ok = init
				if not init:
					if k in self._conf:
						ok = True
					else:
						msg = "key='"+k+"' is not valid."
						self.logger.error(msg)
						raise ConfigurationException(msg)
				if ok:
					self.logger.debug("Configuration[%s] = %s", k, value)
					self._conf[k] = value

	def add_yaml_config(self, yamlConfig, init=False):
		"""
		Add configuration from yaml file path.
		"""
		if yamlConfig is str:
			yamlConfig = Path(yamlConfig)
		with yamlConfig.open('r', encoding="utf-8") as file:
			self.logger.info("Load YAML configuration from '",yamlConfig,"'")
			dict_config = yaml.load(file, Loader=yaml.FullLoader)
			self._load(dict_config, init)
		# print(self._conf)

	def get(self, key):
		"""
		Return value for this key.
		Rturn None if the key is unknown.
		"""
		return self._conf.get(key, None)
