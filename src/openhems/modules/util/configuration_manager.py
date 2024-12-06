"""
Usefull generic configuration manager.
Let allow get configuration by key, init with a default value.
"""

import os
from pathlib import Path
import yaml
import datetime
import shutil
import traceback
from openhems.modules.util.cast_utility import CastUtililty

rootPath = Path(__file__).parents[4]
DEFAULT_PATH = rootPath / "data/openhems_default.yaml"

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
		self._conf = {}
		self._cache = {}
		if defaultPath  is None:
			self.defaultPath = DEFAULT_PATH
		else:
			self.defaultPath = defaultPath
		self.addYamlConfig(self.defaultPath, True)

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
		dictConfig = self.getRawYamlConfig(yamlConfig)
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
		if key=="":
			value = self._conf
		else:
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

	def getRawYamlConfig(self, path=None):
		if path is None:
			path = self.defaultPath
		if path is str:
			path = Path(path)
		with path.open('r', encoding="utf-8") as yamlfile:
			return yaml.load(yamlfile, Loader=yaml.FullLoader)

	def retrieveYamlConfig(self):
		defaultConfig = self.getRawYamlConfig()
		yamlConfig = {}
		it = iter(defaultConfig.keys())
		iterators = [it] # List of current dictionnary'iterators examined
		# Iterate over a tree
		keys = [] # List of current "path"
		dicts = [defaultConfig] # List of current dictionnary examined
		# NB: (If we lost dicts, we lost iterators)
		more = True
		while len(iterators)>0:
			depth = len(iterators)-1
			it = iterators[depth]
			try:
				key = next(it)
				dictio = dicts[depth]
				globalkey = ((".".join(keys))+"." if len(keys)>0 else  "") + key
				value = dictio[key]
				if isinstance(value, dict):
					keys.append(key)
					iterators.append(iter(value.keys()))
					dicts.append(value)
				else:
					myValue = self.get(globalkey)
					# print("globalkey:", globalkey, "; DefaultValue:", 
					# 	value, "; MyValue:", myValue)
					if myValue!=value:
						elem = yamlConfig
						for i,k in enumerate(keys):
							v = elem.get(k)
							if v is None:
								v = {}
								elem[k] = v
							elem = v
						elem[key] = myValue
			except StopIteration as s:
				iterators.pop()
				if len(keys)>0:
					keys.pop()
				dicts.pop()
		# print("Config: ", yamlConfig)
		return yamlConfig

	def save(self, yamlConfFilepath):
		dictValues = self.retrieveYamlConfig()
		if dictValues is None:
			return
		now = datetime.datetime.now()
		if isinstance(yamlConfFilepath, str):
			yamlConfFilepath = Path(yamlConfFilepath)
		if yamlConfFilepath.exists():
			backupFile = str(yamlConfFilepath) + ("."+now.strftime("%Y%m%d%H%M%S"))
			os.rename(yamlConfFilepath, backupFile)
		try:
			with open(yamlConfFilepath, 'w') as outfile:
				yaml.dump(dictValues, outfile, default_flow_style=False)
		except Exception as e:
			self.logger.error(
				"Fail write new version YAML configuration, backup is of '%s'",
				backupFile
			)
			self.logger.error(traceback.format_exc())
			shutil.copyfile(backupFile, yamlConfFilepath)
