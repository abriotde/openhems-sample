
from enum import Enum
from collections import deque
from typing import Final
import logging, os
logger = logging.getLogger(__name__)

from .feeder import Feeder, SourceFeeder, ConstFeeder
from .node import OpenHEMSNode

class HomeStateUpdater:
	cached_ids = dict()
	refresh_id = 0

	def getNetwork(self):
		logger.error("HomeStateUpdater.getNetwork() : To implement in sub-class")

	def updateNetwork(self):
		logger.error("HomeStateUpdater.updateNetwork() : To implement in sub-class")

class OpenHEMSNetwork:

	inout = []
	out = []
	network_updater: HomeStateUpdater = None

	def print(self, logger=None):
		if logger is None:
			logger = print
		logger("OpenHEMSNetwork(")
		logger(" IN : ")
		for elem in self.inout:
			logger("  - "+str(elem.id))
		logger(" OUT : ")
		for elem in self.out:
			logger("  - "+str(elem.id))
		logger(")")

	def __init__(self, network_updater: HomeStateUpdater):
		self.network_updater = network_updater

	def getSchedule(self):
		schedule = dict()
		for node in self.out:
			id = node.id
			sc = node.getSchedule()
			schedule[id] = sc
		return schedule

	def addNode(self, elem: OpenHEMSNode, inNode: bool) -> OpenHEMSNode:

		elem.network = self
		if inNode:
			self.inout.append(elem)
		else:
			self.out.append(elem)
		return elem

	def getCurrentPowerConsumption(self):
		pow = 0
		for elem in self.inout:
			p = elem.getCurrentPower()
			if isinstance(p, str):
				logger.critical("power as string : "+p)
				os._exit(1)
			pow += p
		return pow
	def getCurrentMaxPower(self):
		pow = 0
		for elem in self.inout:
			pow += elem.getCurrentMaxPower()
		return pow
	def getCurrentMinPower(self):
		pow = 0
		for elem in self.inout:
			pow += elem.getCurrentMinPower()
		return pow
	def getMarginPower(self):
		pow = 0
		for elem in self.inout:
			if elem.isOn():
				pow += elem.getMarginPower()
		return pow
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
						pow = elem.getCurrentPower()
						if elem.switchOn(False):
							marginPowerOn += pow
			return 0
		else:
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
							marginPowerOff += elem.maxPower # Not safe, should we use minPower or avgPower... TODO?
			return 0
		return marginPowerOff

	def notify(self, message:str):
		"""
		Send a notification using the appropriate way (Only push to HomeAssistant for the moment).
		"""
		self.network_updater.notify(message)

	def switchOffAll(self):
		logger.info("Network.switchOffAll()")
		# self.print(logger.info)
		powerMargin = self.getCurrentPowerConsumption()
		# self.print(logger.info)
		ok = True
		for elem in self.out:
			if elem.isSwitchable and elem.switchOn(False):
				logger.warning("Fail to switch off ",elem.id)
				ok = False
		return ok

	def updateStates(self):
		self.network_updater.updateNetwork()

	def isGridSourceOn(self):
		# TODO
		return True

	def getBatteryLevel(self, inPercent:bool=True):
		# TODO
		return 0

