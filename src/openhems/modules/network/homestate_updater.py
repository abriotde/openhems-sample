"""
This module aim to abstract home network of connected devices.
It is used to know devices and to switch on/off them.
"""

from typing import Final
import logging
from openhems.modules.util import (
	ConfigurationManager, ConfigurationException,
	CastException, CastUtililty, HoursRanges
)
from .node import ApplianceConstraints
from .outnode import (
	OutNode, Switch, FeedbackSwitch
)
from .inoutnode import (
	PublicPowerGrid, SolarPanel, Battery
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
		self.logger = logging.getLogger(__name__)
		self.network = None
		self.conf = conf
		self.tmp = None # Used to avoid method argument repeated.
		self.warningMessages = []

	def getCycleId(self):
		"""
		Return the refresh Id of the network.
		"""
		return self.network.getCycleId()

	def updateNetwork(self):
		"""
		A function witch update home network and return OpenHEMSNetwork.
		"""
		# self.refreshId += 1 # useless : self.network.getCycleId() replaceIt?

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

	def getFeeder(self, value, expectedType=None, defaultValue=None, nameid="", node=None) -> Feeder:
		"""
		Return a feeder considering
		 This function should be overiden by sub-class
		"""
		del defaultValue, nameid, node
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
		marginPower = self._getFeeder(nodeConf, "marginPower", "int")
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
			stringsPerInverter=stringsPerInverter, marginPower=marginPower)
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

	def _getFeeder(self, conf, key, expectedType=None, node=None) -> Feeder:
		"""
		Return a feeder, search in configuration for default value if not set. 
		"""
		value = conf.get(key)
		if value is None\
			or value=='': # Like None but for not mandatory fields.
			value = self.conf.get( "default.node."+self.tmp+"."+key)
		try:
			feeder = self.getFeeder(value, expectedType, nameid=self.tmp+"."+key, node=node)
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
			except (ConfigurationException, CastException) as e:
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
		maxPower = self._getFeeder(nodeConf, "maxPower", "int")
		nbCycleWithoutPowerForOff = CastUtililty.toTypeInt(nodeConf.get("nbCycleWithoutPowerForOff", 1))
		node = OutNode(nameid, currentPower, maxPower, network=self.network
				, nbCycleWithoutPowerForOff=nbCycleWithoutPowerForOff)
		isOn = nodeConf.get("isOn")
		if isOn is not None and isOn!='':
			isOn = self._getFeeder(nodeConf, "isOn", "bool", node=node)
			priority = nodeConf.get("priority", 50)
			strategyId = nodeConf.get("strategy", None)
			if strategyId is None:
				strategyId = self.network.getDefaultStrategy().id
			node = Switch(node, isOn, strategyId, priority=priority)
			sensor = nodeConf.get("sensor")
			if sensor is not None and sensor!='':
				sensor = self._getFeeder(nodeConf, "sensor", "int")
				target = nodeConf.get("target", None)
				direction = FeedbackSwitch.Direction.UP
				if target is not None:
					if isinstance(target, list) and len(target)==2 and isinstance(target[0], (int, float)):
						# case min/max couple : Exp: [16, 23]
						minmax = FeedbackSwitch.MinMax(target[0], target[1], direction)
						target = HoursRanges(hoursRangesList=[], outRangeCost=minmax)
					elif isinstance(target, (int, float)):
						# case target value : Exp: 16
						target = HoursRanges(hoursRangesList=[], outRangeCost=target)
					else:
						# case complex : [["16h-23h", 15], ["23h-16h", [16, 18]]]
						target = HoursRanges(target)
				node = FeedbackSwitch(node, sensorFeeder=sensor, targeter=target,
						direction=direction)
			condition = nodeConf.get('condition', None)
			if condition is not None:
				node.setCondition(condition)
			constraints = nodeConf.get("constraints", None)
			if constraints is not None:
				constraints = ApplianceConstraints(constraints)
				node.setConstraints(constraints)
		# self.logger.info(node)
		return node
