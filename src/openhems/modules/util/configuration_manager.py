"""
Usefull generic configuration manager.
Let allow get configuration by key, init with a default value.
"""

import os
from pathlib import Path
import datetime
import shutil
import traceback
import yaml
from yaml.scanner import ScannerError
from openhems.modules.util.cast_utility import CastUtililty, CastException

rootPath = Path(__file__).parents[2]
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
	HOOKS = { # Those key are list of class-types following model define in key "default."+hook.
		"network.nodes": "node",
		"server.strategies": "strategy"
	}
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
		self.lastYamlConfFilepath = self.defaultPath

	#pylint: disable=too-many-branches
	def _completeFromModelCB(self, configuration, model, baseKey="", exceptKeys=None):
		"""
		Check if val match recursively to a model wich is an object,
			if not complete with default value.
		"""
		if model is None:
			return configuration
		if exceptKeys is None:
			exceptKeys=[]
		for key, sModel in model.items():
			if key in exceptKeys:
				continue
			value = configuration.get(key)
			defaultValue = value
			if value is None:
				if isinstance(sModel, (float, int, list, str)):
					defaultValue = sModel
					self.logger.debug(
						"ConfigurationManager._completeFromModelCB() : set configuration[%s] = %s",
						baseKey+"."+key, defaultValue)
				elif sModel is None:
					defaultValue = None
				else:
					defaultValue = self._completeFromModel({}, sModel, baseKey+"."+key)
			else:
				classname = sModel.__class__.__name__
				if sModel is None: # Case model not define default value.
					defaultValue = value
				elif classname in ["int", "float", "bool", "str", "list"]:
					try:
						value = CastUtililty.toType(classname, value)
					except CastException as e:
						self.logger.error("Fail to cast %s to type %s : '%s",
						value, sModel.__class__.__name__, e.message)
				elif classname=="dict":
					defaultValue = self._completeFromModel(value, sModel, baseKey+'.'+key)
				else:
					self.logger.error(
						"ConfigurationManager._completeFromModelCB() : Unknown type '%s' for key='%s' : %s.",
						classname, key, model)
				if defaultValue!=value:
					self.logger.debug(
						"ConfigurationManager._completeFromModelCB() : change configuration[%s] = %s to %s",
						baseKey+"."+key, value, defaultValue)
			configuration[key] = defaultValue
		return configuration

	def _completeFromModel(self, configuration, model, baseKey=""):
		"""
		Check if val correspond to a model,
			if not complete with default value.
			The model an be an object representing a choice between classes or a real dict of key/value.
		"""
		selectKeys = { # Keys where we have object as a select choice beetwen classes.
			"": True,
			".publicpowergrid.contract": True
		}
		if selectKeys.get(baseKey.lower()) is None: # Case iterate over object.
			configuration = self._completeFromModelCB(configuration, model, baseKey)
		else:
			classname = configuration.get("class")
			if classname is None:
				self.logger.error(
					"ConfigurationManager._completeFromModel() : No 'class' defined in id='%s'.",
					configuration.get('id',''))
				return None
			myModel = model.get(classname.lower())
			if myModel is None:
				self.logger.error(
					"ConfigurationManager._completeFromModel() : Class='%s' not defined for id='%s' key=%s.",
					classname, configuration.get('id',''), baseKey)
				return None
			configuration = self._completeFromModelCB(
				configuration, myModel, baseKey+"."+classname, ["class"])
		return configuration

	def completeWithDefaults(self):
		"""
		Check if all hooks are correctly defined.
		"""
		for key, hook in self.HOOKS.items():
			model = self.get("default."+hook, deepSearch=True, asTree=True)
			vals = self.get(key)
			if vals is None:
				msg = "Hook '"+key+"' is not defined in configuration."
				self.logger.error(msg)
				raise ConfigurationException(msg)
			if isinstance(vals, list):
				vals2 = []
				change = False
				for conf in vals:
					conf2 = self._completeFromModel(conf, model)
					if conf2 is not None:
						vals2.append(conf2)
						if conf!=conf2:
							change = True
							self.logger.debug(
								"Change configuration[%s][x] = %s to %s",
						 		key, conf, conf2)
				if change:
					self.add(key, vals2)

	def _load(self, dictConfig, init=False, prekey=''):
		"""
		Add configuration from recursive dictionary.
		"""
		if dictConfig is not None:
			# print("_load(",dictConfig,")")
			for key, value in dictConfig.items():
				# print("> ",key," => ", value)
				self.add(key, value, init, prekey)

	def getLastYamlConfFilepath(self):
		"""
		Return the last YAML configuration file path. We consder it as the "main".
		"""
		return self.lastYamlConfFilepath

	def addYamlConfig(self, yamlConfig, init=False):
		"""
		Add configuration from yaml file path.
		"""
		# print("addYamlConfig(",yamlConfig,")")
		try:
			dictConfig = self.getRawYamlConfig(yamlConfig)
		except ScannerError as e:
			msg = (f"Parsing error on '{yamlConfig}' impossible to load."
				" Ignore it witch have big consequences on behaviour. "+str(e))
			self.logger.error(msg)
			raise ConfigurationException(msg) from e
		if dictConfig is not None:
			self._load(dictConfig, init)
		self._cache = {}
		self.lastYamlConfFilepath = yamlConfig
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
				msg = "key='"+k+"' is not valid in "+str(self._conf)+"."
				self.logger.error(msg)
				raise ConfigurationException(msg)
			# self.logger.debug("Configuration[%s] = %s", k, value)
			self._conf[k] = value
		self._cache = {}

	@staticmethod
	def toTree(aDict):
		"""
		Convert a flat dict {"key0.key1": "val"} to a tree dict (with sub-dict : {"key0":{"key1":"val"}}
		"""
		sortedList = sorted(aDict.items())
		retValue = {}
		prevKeys = []
		prevDicts = [retValue]
		for longKey, myValue in (sortedList):
			myKeys = longKey.split(".")
			for i,k in enumerate(myKeys):
				if i>=len(prevKeys):
					prevKeys.append(k)
				elif prevKeys[i]!=k:
					prevKeys[i] = k
				mySDict = prevDicts[i].get(k, {})
				if i+1>=len(prevDicts):
					prevDicts.append(mySDict)
				else:
					prevDicts[i+1] = mySDict
			i = len(myKeys)-1
			value = myValue
			for k in reversed(myKeys):
				prevDicts[i][k] = value
				value = prevDicts[i]
				i -= 1
		return retValue

	def _getDict(self, key, asTree):
		"""
		Return a dict of all sub-keys.
		"""
		if key in self._cache:
			value = self._cache[key]
		else:
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
		if asTree:
			value = self.toTree(value)
		return value

	def get(self, key, expectedType=None, *, defaultValue=None, deepSearch=False, asTree=False):
		"""
		Return value for this key.
		Return None if the key is unknown.
		If deepSearch, we return a dict of all sub-keys.
			NB: It would be better to return a sub-ConfigurationManager...
		"""
		val = self._conf.get(key, defaultValue)
		if val is None:
			if deepSearch:
				val = self._getDict(key, asTree)
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
		"""
		Function to get Raw (Configuration as dict of dict, instead of simple keys)
		 YAML default configuration. 
		"""
		if path is None:
			path = self.defaultPath
		if path is str:
			path = Path(path)
		with path.open('r', encoding="utf-8") as yamlfile:
			return yaml.load(yamlfile, Loader=yaml.FullLoader)

	@staticmethod
	def setYamlConfigKey(yamlConfig, keys, myValue):
		"""
		Set a value for a key in a YAML config with:
		yamlConfig: YAML config as a recursiv dict.
		keys: a list of keys : "a.b.c" = ["key","subkey","subsubkey"] wich is a ConfigurationManager key
		"""
		# print("setYamlConfigKey(",yamlConfig,", ",keys,", ",myValue,")")
		elem = yamlConfig
		l = len(keys)-1
		for i,k in enumerate(keys):
			if i==l:
				elem[k] = myValue
			else:
				v = elem.get(k)
				if v is None:
					v = {}
					elem[k] = v
				elem = v
		return yamlConfig

	def retrieveYamlConfig(self, full=False):
		"""
		Retrieve what should be the YAML config to get that configuration.
		Substract values to default Values from self.defaultPath.
		"""
		defaultConfig = self.getRawYamlConfig()
		yamlConfig = {}
		it = iter(defaultConfig.keys())
		iterators = [it] # List of current dictionnary'iterators examined
		# Iterate over a tree
		keys = [] # List of current "path"
		dicts = [defaultConfig] # List of current dictionnary examined
		# NB: (If we lost dicts, we lost iterators)
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
					if full or myValue!=value:
						keys.append(key)
						yamlConfig = self.setYamlConfigKey(yamlConfig, keys, myValue)
						keys.pop()
			except StopIteration:
				iterators.pop()
				if len(keys)>0:
					keys.pop()
				dicts.pop()
		# print("Config: ", yamlConfig)
		return yamlConfig

	def save(self, yamlConfFilepath):
		"""
		Save the current configuration in a Yaml file.
		"""
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
			with open(yamlConfFilepath, 'w', encoding="utf-8") as outfile:
				yaml.dump(dictValues, outfile, default_flow_style=False)
		except (OSError, yaml.YAMLError):
			self.logger.error(
				"Fail write new version YAML configuration, backup is of '%s'",
				backupFile
			)
			self.logger.error(traceback.format_exc())
			shutil.copyfile(backupFile, yamlConfFilepath)
