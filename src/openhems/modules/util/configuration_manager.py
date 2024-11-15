"""
Usefull generic configuration manager.
Let allow get configuration by key, init with a default value.
"""

from pathlib import Path
from .cast_utility import CastUtililty
import yaml

class ConfigurationException(Exception):
	"""
	Custom Configuration exception.
	"""
	def __init__(self, message, defaultValue=''):
		self.message = message
		self.defaultValue = defaultValue

class ConfigurationManager():
	"""
	Usefull generic configuration manager.
	Let allow get configuration by key.
	1. init with a default value.
	2. Overload with user defined configuration value (If key defined as default)
	3. get the value by key/value dict
	"""
	_instance = None
	def __init__(self, logger, defaultPath=None):
		# print("ConfigurationManager()")
		self.logger = logger
		if defaultPath  is None:
			rootPath = Path(__file__).parents[4]
			defaultPath = rootPath / "data/openhems_default.yaml"
			# print("defaultPath:",defaultPath)
		elif defaultPath is str:
			defaultPath = Path(defaultPath)
		self._conf = {}
		self.addYamlConfig(defaultPath, True)

	def _load(self, dictConfig, init=False, prekey=''):
		"""
		Add configuration from recursive dictionary.
		"""
		# print("_load(",dictConfig,")")
		for key, value in dictConfig.items():
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
					# print("Configuration[",k,"] = ", value)
					self._conf[k] = value

	def addYamlConfig(self, yamlConfig, init=False):
		"""
		Add configuration from yaml file path.
		"""
		# print("addYamlConfig(",yamlConfig,")")
		if yamlConfig is str:
			yamlConfig = Path(yamlConfig)
		with yamlConfig.open('r', encoding="utf-8") as yamlfile:
			self.logger.info("Load YAML configuration from '%s'", yamlConfig)
			dictConfig = yaml.load(yamlfile, Loader=yaml.FullLoader)
			self._load(dictConfig, init)
		# print(self._conf)

	def add(self, key, value):
		"""
		Force a new value for a key.
		"""
		self._conf[key] = value

	def get(self, key, expectedType=None):
		"""
		Return value for this key.
		Rturn None if the key is unknown.
		"""
		val = self._conf.get(key, None)
		if expectedType is not None:
			val = CastUtililty.toType(expectedType, val)
		return val
