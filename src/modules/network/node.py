
from enum import Enum
from collections import deque
from typing import Final
from modules.web import OpenHEMSSchedule
from .feeder import Feeder
CYCLE_HISTORY: Final[int] = 10 # Number of cycle we keep history
import logging
logger = logging.getLogger(__name__)

class OpenHEMSNode:
	id = ""
	params = ""
	network = None
	_isSwitchable = False
	_isOn: Feeder = None
	currentPower: Feeder = 0
	maxPower: Feeder = 2000

	def setId(self, id):
		self.id = id.strip().replace(" ", "_")

	def __init__(self, currentPower, maxPower, isOnFeeder=None):
		self.currentPower = currentPower
		self.maxPower = maxPower
		if isOnFeeder is not None:
			self._isOn = isOnFeeder
			self._isSwitchable = True
		else:
			self._isSwitchable = False

	def setCurrentPower(self, currentPower):
		if len(self.previousPower)>=CYCLE_HISTORY:
			self.previousPower.popleft()
		self.previousPower.append(self.currentPower)
		self.currentPower = currentPower

	def getCurrentPower(self):
		currentPower = self.currentPower.getValue()
		if self._isSwitchable and not self.isOn() and currentPower!=0:
			logger.warning(self.id+" is Off but current power="+str(currentPower))
		logger.info("OpenHEMSNode.getCurrentPower() = "+str(currentPower))
		return currentPower

	def getMaxPower(self):
		return self.maxPower.getValue()

	def estimateNextPower(self):
		"""Estimate what could be the next value of currentPower if there is no change

		This function would like to know if there is a constant growing/decreasing value or a random one or oscilating one...
		:return list[int]: [minValue, bestBet, maxValue]
		"""
		avgDeltaPower = 0
		p0 = self.currentPower
		maxi = len(self.previousPower)
		sum = 0
		lastDiff = 0
		maxDiff = 0
		for i in reversed(range(0, maxi)):
			p1 = self.previousPower[i]
			diff = p1-p0
			if (i==maxi):
				lastDiff = diff
			if (abs(diff)>maxDiff):
				maxDiff = abs(diff)
			sum += diff
			p0 = p1
		avgDiff = sum/maxi
		if (avgDiff>0 and lastDiff>2*avgDiff) \
				or (avgDiff<0 and lastDiff<2*avgDiff):
			curDiff = lastDiff
		else:
			currDiff = avgDiff
		return [self.currentPower-abs(maxDiff), self.currentPower+curDiff, self.currentPower+abs(maxDiff)]

	def isSwitchable(self):
		"""
		"""
		return self._isSwitchable
	def isOn(self):
		"""
		"""
		# print("OpenHEMSNode.isOn(",self.id,")")
		if self._isSwitchable:
			return self._isOn.getValue()
		else:
			return True
	def switchOn(self, connect: bool) -> bool:
		"""
		May not work if it is impossible (No relay) or if it failed.
		
		return bool: False if fail to switchOn/switchOff
		"""
		if self._isSwitchable:
			return self.network.network_updater.switchOn(connect, self)
		else:
			print("Warning : try to switchOn/Off a not switchable device : ",self.id)
			return connect # Consider node is always on network

class OutNode(OpenHEMSNode):

	def __init__(self, id, currentPower, maxPower, isOnFeeder=None):
		OpenHEMSNode.__init__(self, currentPower, maxPower, isOnFeeder)
		self.setId(id)
		self.name = id
		self.schedule = OpenHEMSSchedule(self.id, id)

	def getSchedule(self):
		return self.schedule

class InOutNode(OpenHEMSNode):
	"""
	It is electricity source, it may consume electricity over-production if possible (Battery with MPPT or Sell on public-grid)
	param maxPower: positive value, max power we can consume at a time.
	param minPower: negative value if we can sell or ther is battery, 0 overwise.
	"""
	def __init__(self, currentPower, maxPower, minPower, marginPower) -> None:
		# isAutoAdatative: bool, isControlable: bool, isModulable: bool, isCyclic: bool
		self.previousPower = deque()
		self.currentPower = currentPower
		self.marginPower = marginPower
		self.maxPower = maxPower
		self.minPower = minPower

	def respectConstraints(self, power=None):
		"""Check min/max constraints for power
		
		return bool: true if 'power' respects constraints
		"""
		if power is None:
			power = self.currentPower.getValue()

		if power+self.marginPower.getValue()>self.maxPower.getValue():
			return False
		if power-self.marginPower.getValue()<self.minPower.getValue():
			return False
		return True

	def getCurrentMaxPower(self):
		return self.maxPower.getValue()
	def getCurrentMinPower(self):
		return self.minPower.getValue()
	def getMarginPower(self):
		return self.marginPower.getValue()

	def getSafetyLevel(self):
		"""Get a int value representing how safe is the current power value
		
		return int:
			- 0: unsafe
			- 1: respect constraints but shouldn't on nex loop
			- 2: respect constraints but could be out of constraints next loop
			- 3: Safe values
		"""
		if not self.respectConstraints():
			return 0
		min, avg, max = self.estimateNextPower(self);
		if not self.respectConstraints(avg):
			return 1
		if not (self.respectConstraints(min) or self.respectConstraints(max)):
			return 2
		return 3

class PublicPowerGrid(InOutNode):
	def __init__(self, currentPower, maxPower, minPower, marginPower) -> None:
		super().__init__(currentPower, maxPower, minPower, marginPower)

class SolarPanel(InOutNode):
	def __init__(self, currentPower, maxPower, minPower, marginPower) -> None:
		super().__init__(currentPower, maxPower, minPower, marginPower)
	def getCurrentMaxPower(self):
		return self.currentPower.getValue()

"""
class RTETempoContract(PublicPowerGrid):
	def __init__(self, maxPower, minPower) -> None:
		self.isAutoAdatative = True
		self.isControlable = True
		self.isModulable = False
	def checkConstraints(self):
		if self.currentPower

class Switch(InOutNode):
	def __init__(self, maxPower, minPower) -> None:
		self.isControlable = False
		self.isModulable = False

class CarCharger(Switch):
	def __init__(self, maxPower, minPower, capacity) -> None:
		assert minPower<=0 and maxPower<=0
		self.isControlable = True
		self.isModulable = False

class WaterHeater(InOutNode):
	def __init__(self, maxPower, minPower, capacity) -> None:
		assert minPower<=0 and maxPower<=0
		self.isControlable = True
		self.isModulable = True

class Battery(Switch):
	def __init__(self, maxPower, minPower, capacity) -> None:
		self.isControlable = True
		self.isModulable = False

	def __init__(self, id, use, type) -> None:
		pass
"""

