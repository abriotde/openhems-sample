"""
Usefull generic configuration manager.
Let allow get configuration by key, init with a default value.
"""

from pathlib import Path
import yaml
from openhems.modules.util.cast_utility import CastUtililty

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
		self._cache = {}
		self.addYamlConfig(defaultPath, True)

	def _load(self, dictConfig, init=False, prekey=''):
		"""
		Add configuration from recursive dictionary.
		"""
		# print("_load(",dictConfig,")")
		for key, value in dictConfig.items():
			# print("> ",key," => ", value)
			self.add(key, value, init, prekey)

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
		self._cache = {}
		# print(self._conf)

	def add(self, key, value, init=False, prekey=''):
		"""
		Force a new value for a key.
		"""
		if isinstance(value, dict):
			self._load(value, init, prekey+key+'.')
		else:
			k = prekey+key
			if not init and not k in self._conf:
				msg = "key='"+k+"' is not valid."
				self.logger.error(msg)
				raise ConfigurationException(msg)
			self.logger.debug("Configuration[%s] = %s", k, value)
			# print("Configuration[",k,"] = ", value)
			self._conf[k] = value
		self._cache = {}

	def _getDict(self, key):
		"""
		Return a dict of all sub-keys.
		"""
		if key in self._cache:
			return self._cache[key]
		keyStart = key+'.'
		value = {}
		l = len(keyStart)
		for k, v in self._conf.items():
			if k==key or k.startswith(keyStart):
				newKey = k[l:]
				value[newKey] = v
		self._cache[key] = value
		return value

	def get(self, key, expectedType=None, *, defaultValue=None, deepSearch=False):
		"""
		Return value for this key.
		Return None if the key is unknown.
		If deepSearch, we return a dict of all sub-keys.
			NB: It would be better to return a sub-ConfigurationManager...
		"""
		val = self._conf.get(key, defaultValue)
		if val is None:
			if deepSearch:
				val = self._getDict(key)
				if len(val)==0:
					val = None
			else:
				val = defaultValue
		elif val is str and val=="None":
			val = defaultValue
		elif expectedType is not None:
			val = CastUtililty.toType(expectedType, val)
		return val
