
from enum import Enum
from collections import deque
from typing import Final
CYCLE_HISTORY: Final[int] = 10 # Number of cycle we keep history
POWER_MARGIN: Final[int] = 10 # Number of cycle we keep history

class OpenHEMSNetwork:
	elems = dict()
	in = array()
	out = array()
	def __init__():
		pass

class OpenHEMSNode:
	@staticmethod
	def create(elem: dict):
		id = elem['id']
		use = elem['use']
		type = elem['type']
		o = OpenHEMSNode(id, use, type)

class InOutNode(OpenHEMSNode):
	def __init__(self, id, maxPower, minPower, 
			  isAutoAdatative: bool, isControlable: bool, isModulable: bool, isCyclic: bool) -> None:
		self.id = id
		self.previousPower = deque()
		self.currentPower = 0
		self.powerMargin = POWER_MARGIN
		self.maxPower = maxPower
		self.minPower = minPower
		self.isAutoAdatative = isAutoAdatative
		self.isControlable = isControlable
		self.isModulable = isModulable
		self.isCyclic = isCyclic
	
	def update(self, currentPower):
		if (len(self.previousPower)>=CYCLE_HISTORY):
			self.previousPower.popleft()
		self.previousPower.append(self.currentPower)
		self.currentPower = currentPower

	def estimateNextPower(self):
    	"""Estimate what could be the next value
    	
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
		if (avgDiff>0 and lastDiff>2*avgDiff)
			or (avgDiff<0 and lastDiff<2*avgDiff):
			curDiff = lastDiff
		else:
			currDiff = avgDiff
		return [self.currentPower-abs(maxDiff), self.currentPower+curDiff, self.currentPower+abs(maxDiff)]

	def respectConstraints(self, power=self.currentPower):
		"""Check min/max constraints for power
		
		return bool: true if 'power' respects constraints
		"""
		if power+self.powerMargin>self.maxPower:
			return false
		if power-self.powerMargin<self.minPower:
			return false
		return true

	def getSafetyLevel(self):
		"""Get a int value representing how safe is the current power value
		
		return int:
			- 0: unsafe
			- 1: respect constraints but shouldn't on nex loop
			- 2: respect constraints but could be out of constraints next loop
			- 3: Safe values
		"""
		if ! self.respectConstraints():
			return 0
		min, avg, max = estimateNextPower(self);
		if ! self.respectConstraints(avg):
			return 1
		if ! (self.respectConstraints(min)
				 || self.respectConstraints(max)
			):
			return 2
		return 3

class PublicPowerGrid(InOutNode):
	def __init__(self, maxPower, minPower) -> None:
		self.isAutoAdatative = True
		self.isControlable = True
		self.isModulable = False

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

class SolarPanel(InOutNode):
	def __init__(self, maxPower, minPower, capacity) -> None:
		assert minPower>=0 and maxPower>=0
		self.isControlable = False
		self.isModulable = False

	def __init__(self, id, use, type) -> None:
		pass
