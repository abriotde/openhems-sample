"""
This module aim to abstract home network of connected devices.
It is used to know devices and to switch on/off them.
"""

from typing import Final
import logging
import os
import copy
from openhems.modules.util.configuration_manager import ConfigurationManager, ConfigurationException
from openhems.modules.util.notification_manager import NotificationManager
from .node import (
	OpenHEMSNode, InOutNode, OutNode, PublicPowerGrid, SolarPanel, Battery
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

	def initNetwork(self):
		"""
		Can be overiden by sub-class if neeeded.
		This function is called to initialyze network.
		"""

	# pylint: disable=unused-argument
	def getFeeder(self, value, expectedType=None, defaultValue=None) -> Feeder:
		"""
		Return a feeder considering
		 This function should be overiden by sub-class
		"""
		return SourceFeeder(value, self, expectedType)

	def getPublicPowerGrid(self, nameid, nodeConf):
		"""
		Return a PublicPowerGrid according nodeConf 
		"""
		self.tmp = "publicpowergrid"
		currentPower = self._getFeeder(nodeConf, "currentPower", "int")
		powerMargin = self._getFeeder(nodeConf, "powerMargin", "int")
		maxPower = self._getFeeder(nodeConf, "maxPower", "int")
		minPower = self._getFeeder(nodeConf, "minPower", "int")
		contract = nodeConf.get("contract")
		node = PublicPowerGrid(currentPower, maxPower, minPower, powerMargin,
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
		node = SolarPanel(currentPower, maxPower,
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
		maxPowerIn = self._getFeeder(nodeConf, "maxPowerIn", "int")
		maxPowerOut = self._getFeeder(nodeConf, "maxPowerOut", "int")
		marginPower = self._getFeeder(nodeConf, "marginPower", "int")
		currentLevel = self._getFeeder(nodeConf, "currentLevel", "float")
		lowLevel = self._getFeeder(nodeConf, "lowLevel", "float")
		hightLevel = self._getFeeder(nodeConf, "hightLevel", "float")
		node = Battery(capacity, currentPower, maxPowerIn=maxPowerIn,
			maxPowerOut=maxPowerOut, marginPower=marginPower,
			currentLevel=currentLevel, lowLevel=lowLevel, hightLevel=hightLevel)
		# self.logger.info(node)
		return node

	# pylint: disable=unused-argument
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

	def _getNetwork(self, networkConf):
		"""
		Initialyze network according to it's configuration.
		"""
		i = 0
		for e in networkConf:
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
		maxPower = self._getFeeder(nodeConf, "maxPower", "int")
		isOn = self._getFeeder(nodeConf, "isOn", "bool")
		node = OutNode(nameid, currentPower, maxPower, isOn)
		# self.logger.info(node)
		return node

	def getNetwork(self, logger): # -> OpenHEMSNetwork:
		"""
		Explore the home device network available with Home-Assistant.
		"""
		self.network = OpenHEMSNetwork(self, logger)
		self.initNetwork()
		self._getNetwork(self.conf.get("network.nodes"))
		self.network.print(self.logger.info)
		return self.network

class OpenHEMSNetwork:
	"""
	This class aim to abstract home network of connected devices.
	It is used to know devices and to switch on/off them.
	"""
	networkUpdater: HomeStateUpdater = None

	def print(self, printer=None):
		"""
		Print OpenHEMSNetwork as human readable string
		"""
		if printer is None:
			printer = print
		printer("OpenHEMSNetwork(")
		printer(" IN : ")
		for elem in self.getAll("inout"):
			printer("  - "+str(elem))
		printer(" OUT : ")
		for elem in self.getAll("out"):
			printer("  - "+str(elem))
		printer(")")

	def __init__(self, networkUpdater: HomeStateUpdater, logger):
		self.networkUpdater = networkUpdater
		self.nodes = []
		self.notificationManager = NotificationManager(self.networkUpdater)
		self._elemsCache = {}
		self.logger = logger

	def getWarningMessages(self):
		"""
		Return a list of important problems during initializing Network.
		"""
		return self.networkUpdater.warningMessages

	def getSchedule(self):
		"""
		Return scheduled planning.
		"""
		schedule = {}
		for node in self.getAll("out"):
			myid = node.id
			sc = node.getSchedule()
			schedule[myid] = sc
		return schedule

	def addNode(self, elem: OpenHEMSNode) -> OpenHEMSNode:
		"""
		Add a node.
		"""
		elem.network = self
		self.nodes.append(elem)
		self._elemsCache = {}
		return elem

	def getCurrentPowerConsumption(self):
		"""
		Get current power consumption by all network..
		"""
		globalPower = 0
		for elem in self.getAll("inout"):
			p = elem.getCurrentPower()
			if isinstance(p, str):
				self.logger.critical("power as string : '%s'", p)
				os._exit(1)
			globalPower += p
		return globalPower

	def _getAll(self, filterId, elemFilter=None):
		"""
		Return Out nodes, filtered by strategy=strategyId if set.
		!!! WARNING !!! filterId and elemFilter must be bijectiv (one-to-one)
		"""
		out = self._elemsCache.get(filterId, None)
		if out is None:
			if elemFilter is None:
				filters = {
					"inout" : (lambda x: isinstance(x, InOutNode)),
					"out" : (lambda x: isinstance(x, OutNode)),
					"publicpowergrid" : (lambda x: isinstance(x, PublicPowerGrid)),
					"battery" : (lambda x: isinstance(x, Battery)),
					"solarpanel" : (lambda x: isinstance(x, SolarPanel)),
				}
				elemFilter = filters.get(filterId, None)
			if elemFilter is not None:
				out = list(filter(elemFilter, self.nodes))
			elif filterId=="":
				out = self.nodes
			else:
				self.logger.error("Network.getAll() : unknown filterId '%s'",
					 filterId)
				out = None
			self._elemsCache[filterId] = out
		return out

	def getAll(self, filterId):
		"""
		Same as private _getAll() except that we can't set custom elemFilter
		 to avoid incoherence between elemFilter AND filterId
		"""
		return self._getAll(filterId)

	def _sumNodesValues(self, filterId, defaultFilter, function):
		"""
		Sum all values from nodes (filtered by filterId).
		"""
		if filterId is None:
			filterId = defaultFilter
		globalPower= 0
		for elem in self._getAll(filterId):
			globalPower += function(elem)
		return globalPower

	def getMaxPower(self, filterId=None):
		"""
		Get current maximum power consumption possible.
		"""
		return self._sumNodesValues(filterId, "inout", (lambda x: x.getMaxPower()))

	def getMinPower(self, filterId=None):
		"""
		Get current minimum power consumption possible.
		0 mean, we can't give back power to network grid.
		"""
		return self._sumNodesValues(filterId, "inout", (lambda x: x.getMinPower()))
	def getMarginPower(self, filterId=None):
		"""
		Return margin power
		(Power to keep before considering extrem value)
		"""
		return self._sumNodesValues(filterId, "inout", (lambda x: x.getMarginPower()))

	def getMarginPowerOn(self):
		"""
		Get how many power we can add safely
		"""
		maxPower = self.getMaxPower()
		currentPower = self.getCurrentPowerConsumption()
		marginPower = self.getMarginPower()
		marginPowerOn = maxPower-marginPower-currentPower
		if marginPowerOn<0: # Need to switch off some elements
			while marginPowerOn<0:
				for elem in self.getAll("out"):
					if elem.isSwitchable() and elem.isOn():
						power = elem.getCurrentPower()
						if elem.switchOn(False):
							marginPowerOn += power
			return 0
		return maxPower-(currentPower+marginPower)
	def getMarginPowerOff(self):
		"""
		Get how many power we can remove safely (Case we do not want to over produce)
		"""
		minPower = self.getMinPower()
		currentPower = self.getCurrentPowerConsumption()
		marginPower = self.getMarginPower()
		marginPowerOff = (currentPower-marginPower)-minPower
		if marginPowerOff<0: # Need to switch on some elements
			while marginPowerOff<0:
				for elem in self.getAll("out"):
					if elem.isSwitchable() and not elem.isOn():
						if elem.switchOn(True):
							marginPowerOff += elem.maxPower
							# Not safe, should we use minPower or avgPower... TODO?
			return 0
		return marginPowerOff

	def notify(self, message:str):
		"""
		Send a notification using the appropriate way 
		(Only push to HomeAssistant for the moment).
		"""
		self.notificationManager.notify(message)

	def switchOffAll(self):
		"""
		Switch of all connected devices.
		"""
		self.logger.info("Network.switchOffAll()")
		# self.print(logger.info)
		# powerMargin = self.getCurrentPowerConsumption()
		# self.print(logger.info)
		ok = True
		for elem in self.getAll("out"):
			if elem.isSwitchable and elem.switchOn(False):
				self.logger.warning("Fail to switch off '%s'",elem.id)
				ok = False
		return ok

	def updateStates(self):
		"""
		Update network state using the NetworkUpdater
		"""
		self.networkUpdater.updateNetwork()

	def isGridSourceOn(self):
		"""
		Return true if grid source is available (even if no power is used)
		"""
		# TODO
		return True

	def getBattery(self) -> Battery:
		"""
		Return a battery representing the sum of all battery.
		"""
		batteries = self.getAll("battery")
		l = len(batteries)
		if l<1:
			return Battery(0, 0)
		if l==1:
			return batteries[0]
		# TODO
		return copy.copy(batteries[0])

	def getOffPeakHoursRanges(self):
		"""
		Return a concatenation of all offpeak ours off sources.
		"""
		offpeakhours = []
		nb = 0
		for elem in self.getAll("publicpowergrid"):
			offpeakhours = elem.getContract().getOffPeakHoursRanges()
			nb += 1
		if nb==0:
			self.logger.warning("No PublicPowerGrid on the network.")
		return offpeakhours
