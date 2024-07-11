
from enum import Enum
from collections import deque
from typing import Final
CYCLE_HISTORY: Final[int] = 10 # Number of cycle we keep history
POWER_MARGIN: Final[int] = 10 # Number of cycle we keep history

class OpenHEMSNode:
	id = ""
	params = ""
	network = None
	isSwitchable = True
	isOn = True
	currentPower = 0
	maxPower = 2000

	def setCurrentPower(self, currentPower):
		if len(self.previousPower)>=CYCLE_HISTORY:
			self.previousPower.popleft()
		self.previousPower.append(self.currentPower)
		self.currentPower = currentPower

	def getCurrentPower(self):
		if not self.isOn() and self.currentPower==0:
			print("Warning : ",self.id," is Off but current power=",self.currentPower)
		return self.currentPower

	def getMaxPower(self):
		return self.maxPower

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
		return True
	def isOn(self):
		"""
		"""
		return True
	def switchOn(self, connect: bool) -> bool:
		"""
		May not work if it is impossible (No relay) or if it failed.
		
		return bool: False if fail to switchOn/switchOff
		"""
		if isSwitchable:
			return self.network.network_updater.switchOn(connect, self.params)
		else:
			return connect # Consider node is always on network

class HomeStateUpdater:

	def getNetwork(self):
		print("HomeStateUpdater.getNetwork() : To implement in sub-class")

	def updateNetwork(self):
		print("HomeStateUpdater.updateNetwork() : To implement in sub-class")

class OpenHEMSNetwork:

	inout = dict()
	out = dict()
	network_updater: HomeStateUpdater = None

	def __init__(self, network_updater: HomeStateUpdater):
		self.network_updater = network_updater

	def createNode(params: dict) -> OpenHEMSNode:
		elem = None
		type = params['type']
		if type=="InOutNode":
			elem = InOutNode(params['maxPower'], params['minPower'], params['powerMargin'])
			self.inout[elem.id] = elem
		else:
			print("Error : OpenHEMSNode.create(",params,") : Unknwon type.")
			exit(1);
		elem.id = elem['id']
		elem.params = params
		elem.network = self
		self.elems[elem.id] = elem
		return elem

	def getCurrentPower(self):
		pow = 0
		for elem in self.inout:
			pow += elem.getCurrentPower()
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
				pow += elem.marginPower
		return pow
	def getMarginPowerOn(self):
		"""
		Get how many power we can add safely
		"""
		maxPower = self.getCurrentMaxPower()
		currentPower = self.getCurrentPower()
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
		currentPower = self.getCurrentPower()
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
			

	def updateStates(self):
		self.network_updater.updateNetwork()

class InOutNode(OpenHEMSNode):
	"""
	It is electricity source, it may consume electricity over-production if possible (Battery with MPPT or Sell on public-grid)
	param maxPower: positive value, max power we can consume at a time.
	param minPower: negative value if we can sell or ther is battery, 0 overwise.
	"""
	def __init__(self, maxPower, minPower=0, powerMargin=POWER_MARGIN) -> None:
		# isAutoAdatative: bool, isControlable: bool, isModulable: bool, isCyclic: bool
		self.previousPower = deque()
		self.currentPower = 0
		self.powerMargin = POWER_MARGIN
		self.maxPower = maxPower
		self.minPower = minPower

	def respectConstraints(self, power=None):
		"""Check min/max constraints for power
		
		return bool: true if 'power' respects constraints
		"""
		if power is None:
			power = self.currentPower
		if power+self.powerMargin>self.maxPower:
			return false
		if power-self.powerMargin<self.minPower:
			return false
		return true

	def getCurrentMaxPower(self):
		return self.maxPower
	def getCurrentMinPower(self):
		return self.minPower

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
	def __init__(self, maxPower, minPower=0, powerMargin=POWER_MARGIN) -> None:
		super()

class SolarPanel(InOutNode):
	def __init__(self, maxPower, minPower=0, powerMargin=POWER_MARGIN) -> None:
		super()
	def getCurrentMaxPower(self):
		return self.currentPower

		
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

