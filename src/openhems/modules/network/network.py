"""
This module aim to abstract home network of connected devices.
It is used to know devices and to switch on/off them.
"""

from typing import Final
import logging
import os
import copy
from .node import OpenHEMSNode, InOutNode, PublicPowerGrid, SolarPanel, Battery

POWER_MARGIN: Final[int] = 10 # Margin of power consumption for security
logger = logging.getLogger(__name__)

class HomeStateUpdater:
	"""
	This is an abstract class to update OpenHEMSNetwork
	 ignoring the real source of the update.
	Today only Home-Assistant updater is implemented (HomeAssistantAPI).
	"""
	cached_ids = {}
	refresh_id = 0

	def getNetwork(self):
		"""
		A function witch inspect home network and return OpenHEMSNetwork.
		"""
		logger.error("HomeStateUpdater.getNetwork() : To implement in sub-class")

	def updateNetwork(self):
		"""
		A function witch update home network and return OpenHEMSNetwork.
		"""
		logger.error("HomeStateUpdater.updateNetwork() : To implement in sub-class")

class OpenHEMSNetwork:
	"""
	This class aim to abstract home network of connected devices.
	It is used to know devices and to switch on/off them.
	"""
	network_updater: HomeStateUpdater = None

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

	def __init__(self, network_updater: HomeStateUpdater):
		self.network_updater = network_updater
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
				logger.critical("power as string : {p}")
				os._exit(1)
			globalPower += p
		return globalPower
	def getCurrentMaxPower(self):
		"""
		Get current maximum power consumption possible.
		"""
		globalPower= 0
		for elem in self.inout:
			globalPower += elem.getCurrentMaxPower()
		return globalPower
	def getCurrentMinPower(self):
		"""
		Get current minimum power consumption possible.
		0 mean, we can't give back power to network grid.
		"""
		globalPower = 0
		for elem in self.inout:
			globalPower += elem.getCurrentMinPower()
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
		maxPower = self.getCurrentMaxPower()
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
		minPower = self.getCurrentMinPower()
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
		self.network_updater.notify(message)

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
		self.network_updater.updateNetwork()

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
			return Battery(0, 0, 0, 0, 0)
		if l==1:
			return self.battery[0]
		# TODO
		return copy.copy(self.battery[0])
