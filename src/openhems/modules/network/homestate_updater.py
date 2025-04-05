"""
This module aim to abstract home network of connected devices.
It is used to know devices and to switch on/off them.
"""

from typing import Final
import logging
from openhems.modules.util.configuration_manager import ConfigurationManager, ConfigurationException
from .node import (
	OutNode, PublicPowerGrid, SolarPanel, Battery
)
from .feeder import Feeder, SourceFeeder

POWER_MARGIN: Final[int] = 10 # Margin of power consumption for security

class HomeStateUpdaterException(Exception):
	"""
	Custom Configuration exception.
	"""
	def __init__(self, message, defaultValue=''):
		self.message = message
		self.defaultValue = defaultValue

class HomeStateUpdater:
	"""
	This is an abstract class to update OpenHEMSNetwork
	 ignoring the real source of the update.
	Today only Home-Assistant updater is implemented (HomeAssistantAPI).
	"""
	def __init__(self, conf:ConfigurationManager) -> None:
		self.cachedIds = {}
		self.refreshId = 0
		self.logger = logging.getLogger(__name__)
		self.network = None
		self.conf = conf
		self.tmp = None # Used to avoid method argument repeated.
		self.warningMessages = []

	def getCacheId(self):
		"""
		Return the refresh Id of the network.
		"""
		return self.refreshId

	def updateNetwork(self):
		"""
		A function witch update home network and return OpenHEMSNetwork.
		"""
		self.refreshId += 1

	def switchOn(self, isOn, _):
		"""
		return: True if the switch is on after, False else
		"""
		self.logger.error("switchOn() should be implemented in sub-class.")
		return not isOn

	def notify(self, message):
		"""
		A function witch notify the Network,
		 this should be seen easily by the end user.
		"""
		self.logger.info(message)

	def initNetwork(self, network):
		"""
		Can be overiden by sub-class if neeeded.
		This function is called to initialyze network.
		"""
		self.network = network

	def getFeeder(self, value, expectedType=None, defaultValue=None) -> Feeder:
		"""
		Return a feeder considering
		 This function should be overiden by sub-class
		"""
		del defaultValue
		return SourceFeeder(value, self, expectedType)

	def getPublicPowerGrid(self, nameid, nodeConf):
		"""
		Return a PublicPowerGrid according nodeConf 
		"""
		self.tmp = "publicpowergrid"
		currentPower = self._getFeeder(nodeConf, "currentPower", "int")
		marginPower = self._getFeeder(nodeConf, "marginPower", "int")
		maxPower = self._getFeeder(nodeConf, "maxPower", "int")
		minPower = self._getFeeder(nodeConf, "minPower", "int")
		contract = nodeConf.get("contract")
		# print("getPublicPowerGrid() : marginPower=", marginPower, nodeConf)
		node = PublicPowerGrid(nameid, currentPower, maxPower, minPower, marginPower,
			contract, self)
		# self.logger.info(node)
		return node

	def getSolarPanel(self, nameid, nodeConf):
		"""
		Return a SolarPanel according nodeConf 
		"""
		self.tmp = "solarpanel"
		currentPower = self._getFeeder(nodeConf, "currentPower", "int")
		maxPower = self._getFeeder(nodeConf, "maxPower", "int")
		moduleModel = self._getFeeder(nodeConf, "moduleModel", "str")
		inverterModel = self._getFeeder(nodeConf, "inverterModel", "str")
		tilt = self._getFeeder(nodeConf, "tilt", "float")
		azimuth = self._getFeeder(nodeConf, "azimuth", "int")
		modulesPerString = self._getFeeder(nodeConf, "modulesPerString", "int")
		stringsPerInverter = self._getFeeder(nodeConf, "stringsPerInverter", "int")
		node = SolarPanel(nameid, currentPower, maxPower,
			moduleModel=moduleModel, inverterModel=inverterModel,
			tilt=tilt, azimuth=azimuth,
			modulesPerString=modulesPerString,
			stringsPerInverter=stringsPerInverter)
		# self.logger.info(str(node))
		return node

	def getBattery(self, nameid, nodeConf):
		"""
		Return a Battery according nodeConf 
		"""
		self.tmp = "battery"
		currentPower = self._getFeeder(nodeConf, "currentPower", "int")
		capacity = self._getFeeder(nodeConf, "capacity", "int")
		currentLevel = self._getFeeder(nodeConf, "currentLevel", "float")
		lowLevel = self._getFeeder(nodeConf, "lowLevel", "float")
		targetLevel = self._getFeeder(nodeConf, "targetLevel", "float")
		highLevel = self._getFeeder(nodeConf, "highLevel", "float")
		efficiencyIn = self._getFeeder(nodeConf, "efficiencyIn", "float")
		maxPowerIn = self._getFeeder(nodeConf, "maxPowerIn", "int")
		maxPowerOut = self._getFeeder(nodeConf, "maxPowerOut", "int")
		efficiencyOut = self._getFeeder(nodeConf, "efficiencyOut", "float")
		node = Battery(nameid, capacity, currentPower,
			maxPowerOut=maxPowerOut, maxPowerIn=maxPowerIn,
			currentLevel=currentLevel, lowLevel=lowLevel, highLevel=highLevel,
			targetLevel=targetLevel,
			efficiencyIn=efficiencyIn, efficiencyOut=efficiencyOut)
		# self.logger.info(node)
		return node

	def _getFeeder(self, conf, key, expectedType=None) -> Feeder:
		"""
		Return a feeder, search in configuration for default value if not set. 
		"""
		value = conf.get(key)
		if value is None:
			value = self.conf.get( "default.node."+self.tmp+"."+key)
		try:
			feeder = self.getFeeder(value, expectedType)
		except ValueError as e:
			raise ConfigurationException(
				"Impossible to convert "+key+" = '"+value
				+"' to type "+expectedType
				+" for node '"+self.tmp+"'", 0
			) from e
		if feeder is None:
			msg = "Argument '"+key+"' is required for node '"+self.tmp+"'"
			self.logger.critical(msg)
			raise ConfigurationException(msg)
		return feeder

	def getNetwork(self, networkConf):
		"""
		Initialyze network according to it's configuration.
		"""
		# print("HomestateUpdater._getNetwork()")
		i = 0
		for e in networkConf:
			# print("Node: ",e)
			try:
				classname = e.get("class", "unspecified").lower()
				node = None
				nameid = e.get("id", f"node_{i}")
				i += 1
				if classname == "switch":
					node = node = self.getSwitch(nameid, e)
				elif classname == "publicpowergrid":
					node = self.getPublicPowerGrid(nameid, e)
				elif classname == "solarpanel":
					node = self.getSolarPanel(nameid, e)
				elif classname == "battery":
					node = self.getBattery(nameid, e)
				else:
					msg = f"HomeAssistantAPI.getNetwork : Unknown classname '{classname}'"
					self.logger.critical(msg)
					raise ConfigurationException(msg)
				self.network.addNode(node)
			except ConfigurationException as e:
				msg = f"Impossible to load {classname}({nameid}) due to "+str(e)
				self.logger.error(msg)
				self.warningMessages.append(msg)

	def getSwitch(self, nameid, nodeConf):
		"""
		Return a OpenHEMSNode representing a switch
		 according to it's YAML configuration.
		"""
		self.tmp = "switch"
		currentPower = self._getFeeder(nodeConf, "currentPower", "int")
		strategyId = nodeConf.get("strategy", None)
		if strategyId is None:
			strategyId = self.network.getDefaultStrategy().id
		maxPower = self._getFeeder(nodeConf, "maxPower", "int")
		isOn = self._getFeeder(nodeConf, "isOn", "bool")
		priority = nodeConf.get("priority", 50)
		node = OutNode(nameid, strategyId, currentPower, maxPower, isOn, priority=priority)
		# self.logger.info(node)
		return node
