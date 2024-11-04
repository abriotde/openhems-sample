"""
Usefull generic configuration manager.
Let allow get configuration by key, init with a default value.
"""

from pathlib import Path
import yaml

class ConfigurationException(Exception):
	"""
	Custom Configuration exception.
	"""
	def __init__(self, message, defaultValue=''):
		self.message = message
		self.defaultValue = defaultValue

class Singleton(type):
	"""
	To implement singleton easily in ConfigurationManager
	"""
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
			rootPath = Path(__file__).parents[4]
			defaultPath = rootPath / "data/openhems_default.yaml"
			print("defaultPath:",defaultPath)
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
					print("Configuration[",k,"] = ", value)
					self._conf[k] = value

	def addYamlConfig(self, yamlConfig, init=False):
		"""
		Add configuration from yaml file path.
		"""
		if yamlConfig is str:
			yamlConfig = Path(yamlConfig)
		with yamlConfig.open('r', encoding="utf-8") as file:
			self.logger.info("Load YAML configuration from '",yamlConfig,"'")
			dictConfig = yaml.load(file, Loader=yaml.FullLoader)
			self._load(dictConfig, init)
		# print(self._conf)

	def get(self, key):
		"""
		Return value for this key.
		Rturn None if the key is unknown.
		"""
		return self._conf.get(key, None)
