"""
This module aim to abstract home network of connected devices.
It is used to know devices and to switch on/off them.
"""

from typing import Final
import logging
import os
import copy
from openhems.modules.util.configuration_manager import ConfigurationManager
from .node import (
	OpenHEMSNode, InOutNode, OutNode, PublicPowerGrid, SolarPanel, Battery
)
from .feeder import Feeder, SourceFeeder

POWER_MARGIN: Final[int] = 10 # Margin of power consumption for security
logger = logging.getLogger(__name__)

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
		self.network = None
		self.conf = conf

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
	def getFeeder(self, conf, key, expectedType=None, defaultValue=None) -> Feeder:
		"""
		Return a feeder considering
		 This function should be overiden by sub-class
		"""
		return SourceFeeder(key, self, expectedType)

	def getNetworkIn(self, networkConf):
		"""
		Initialyze "in" network part.
		"""
		# init Feeders
		for e in networkConf:
			classname = e["class"].lower()
			currentPower = self.getFeeder(e, "currentPower", "int")
			powerMargin = self.getFeeder(e, "powerMargin", "int", POWER_MARGIN)
			maxPower = self.getFeeder(e, "maxPower", "int")
			minPower = self.getFeeder(e, "minPower", "int", 0)
			node = None
			if classname == "publicpowergrid":
				node = PublicPowerGrid(currentPower, maxPower, minPower, powerMargin)
			elif classname == "solarpanel":
				node = SolarPanel(currentPower, maxPower, minPower, powerMargin)
			elif classname == "battery":
				lowLevel = self.getFeeder(e, "lowLevel", "int", POWER_MARGIN)
				hightLevel = self.getFeeder(e, "hightLevel", "int", POWER_MARGIN)
				capacity = self.getFeeder(e, "capaciity", "int", POWER_MARGIN)
				currentLevel = self.getFeeder(e, "level", "int", 0)
				node = Battery(currentPower, maxPower, capacity, currentLevel,
					powerMargin=powerMargin, minPower=minPower, lowLevel=lowLevel,
					hightLevel=hightLevel)
			else:
				self.logger.critical("HomeAssistantAPI.getNetwork : "
					"Unknown classname '{classname}'")
				os._exit(1)
			if "id" in e.keys():
				node.id = e["id"]
			# print(node)
			self.network.addNode(node)

	def getSwitch(self, nameid, nodeConf):
		"""
		Return a OpenHEMSNode representing a switch
		 according to it's YAML configuration.
		"""
		currentPower = self.getFeeder(nodeConf, "currentPower", "int")
		isOn = self.getFeeder(nodeConf, "isOn", "bool", True)
		maxPower = self.getFeeder(nodeConf, "maxPower", "int", 2000)
		return OutNode(nameid, currentPower, maxPower, isOn)

	def getNetworkOut(self, networkConf):
		"""
		Initialyze "out" network part.
		"""
		i = 0
		for e in networkConf:
			classname = e["class"].lower()
			node = None
			nameid = e.get("id", f"node_{i}")
			i += 1
			if classname == "switch":
				node = self.getSwitch(nameid, e)
			else:
				self.logger.critical("HomeStateUpdater.getNetworkOut : "
					"Unknown classname '%s'", classname)
				os._exit(1)
			if node is not None:
				self.network.addNode(node)
			else:
				self.logger.critical("HomeStateUpdater.getNetworkOut : "
					"Fail get Node '%s'", str(e))
				os._exit(1)

	def getNetwork(self): # -> OpenHEMSNetwork:
		"""
		Explore the home device network available with Home-Assistant.
		"""
		self.network = OpenHEMSNetwork(self)
		self.initNetwork()
		self.getNetworkIn(self.conf.get("network.in"))
		self.getNetworkOut(self.conf.get("network.out"))
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
		for elem in self.inout:
			printer("  - "+str(elem.id))
		printer(" OUT : ")
		for elem in self.out:
			printer("  - "+str(elem.id))
		printer(")")

	def __init__(self, networkUpdater: HomeStateUpdater):
		self.networkUpdater = networkUpdater
		self.inout = []
		self.out = []
		self.battery = []
		self.publicpowergrid = []
		self.solarpanel = []

	def getSchedule(self):
		"""
		Return scheduled planning.
		"""
		schedule = {}
		for node in self.out:
			myid = node.id
			sc = node.getSchedule()
			schedule[myid] = sc
		return schedule

	def addNode(self, elem: OpenHEMSNode) -> OpenHEMSNode:
		"""
		Add a node.
		"""
		elem.network = self
		if isinstance(elem, InOutNode):
			self.inout.append(elem)
			if isinstance(elem, Battery):
				self.battery.append(elem)
			elif isinstance(elem, PublicPowerGrid):
				self.publicpowergrid.append(elem)
			elif isinstance(elem, SolarPanel):
				self.solarpanel.append(elem)
		else:
			self.out.append(elem)
		return elem

	def getCurrentPowerConsumption(self):
		"""
		Get current power consumption by all network..
		"""
		globalPower = 0
		for elem in self.inout:
			p = elem.getCurrentPower()
			if isinstance(p, str):
				logger.critical("power as string : '%s'", p)
				os._exit(1)
			globalPower += p
		return globalPower
	def getMaxPower(self):
		"""
		Get current maximum power consumption possible.
		"""
		globalPower= 0
		for elem in self.inout:
			globalPower += elem.getMaxPower()
		return globalPower
	def getMinPower(self):
		"""
		Get current minimum power consumption possible.
		0 mean, we can't give back power to network grid.
		"""
		globalPower = 0
		for elem in self.inout:
			globalPower += elem.getMinPower()
		return globalPower
	def getMarginPower(self):
		"""
		Return margin power
		(Power to keep before considering extrem value)
		"""
		globalPower = 0
		for elem in self.inout:
			if elem.isOn():
				globalPower += elem.getMarginPower()
		return globalPower
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
				for elem in self.out:
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
				for elem in self.out:
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
		self.networkUpdater.notify(message)

	def switchOffAll(self):
		"""
		Switch of all connected devices.
		"""
		logger.info("Network.switchOffAll()")
		# self.print(logger.info)
		# powerMargin = self.getCurrentPowerConsumption()
		# self.print(logger.info)
		ok = True
		for elem in self.out:
			if elem.isSwitchable and elem.switchOn(False):
				logger.warning("Fail to switch off '%s'",elem.id)
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
		l = len(self.battery)
		if l<1:
			return Battery(0, 0, 0, 0)
		if l==1:
			return self.battery[0]
		# TODO
		return copy.copy(self.battery[0])
