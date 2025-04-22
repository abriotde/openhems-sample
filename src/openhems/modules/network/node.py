"""
Represent device of home network
"""

import logging

from typing import Final
from collections import deque, OrderedDict
from openhems.modules.util import CastUtililty, ConfigurationException
from .feeder import Feeder

CYCLE_HISTORY: Final[int] = 10 # Number of cycle we keep history
logger = logging.getLogger(__name__)

class ApplianceConstraints():
	"""
	Appliance constraints : Constraints to always chek when the appliance is on or before switching on/off.
	"""
	def __init__(self, node, configuration:dict):
		self.minPower = configuration.get('minPower', None)
		self.maxPower = configuration.get('maxPower', None)
		# durations are in seconds
		self.node = node
		self.minDurationOn = configuration.get('minDurationOn', None)
		self.minDurationOff = configuration.get('minDurationOff', None)
		self.maxDurationOn = configuration.get('maxDurationOn', None)
		self.maxDurationOff = configuration.get('maxDurationOff', None)
		self._duration = 0
		self._isOn = None

	def check(self):
		"""
		:return: max power of the appliance
		"""
		if self.minPower is not None or self.maxPower is not None:
			currentPower = self.node.getCurrentPower()
			if currentPower is None:
				self.node.logger.warning("ApplianceConstraints.check() : currentPower is None")
				return False
			if self.minPower is not None and currentPower<self.minPower:
				self.node.logger.warning("Offending minPower (%d) > currentPower (%d)", self.minPower, currentPower)
				self.node.switchOn(False)
				return False
			if self.maxPower is not None and currentPower>self.maxPower:
				self.node.logger.warning("Offending maxPower (%d) < currentPower (%d)", self.maxPower, currentPower)
				self.node.switchOn(False)
				return False
		if self._isOn:
			if self._duration>self.maxDurationOn:
				self.node.logger.warning("Offending maxDurationOn (%d) < currentDuration (%d)", self.maxDurationOn, self._duration)
				self.node.switchOn(False)
				return False
		else:
			if self._duration>self.maxDurationOff:
				self.node.logger.warning("Offending maxDurationOff (%d) < currentDuration (%d)", self.maxDurationOff, self._duration)
				self.node.switchOn(True)
				return False
		return True

	def switch(self, on):
		"""
		Reset durations
		"""
		if self._isOn:
			if self._duration<self.minDurationOn and not on:
				self.node.logger.warning("Offending minDurationOn (%d) > currentDuration (%d)", self.maxDurationOn, self._duration)
				self.node.switchOn(False)
				return False
		else:
			if self._duration<self.minDurationOff and on:
				self.node.logger.warning("Offending minDurationOff (%d) > currentDuration (%d)", self.maxDurationOff, self._duration)
				self.node.switchOn(True)
				return False
		self._isOn = on
		self._duration = 0
		return True

	def decrementTime(self):
		"""
		Decrease time of schedule and return remaining time.
		"""
		self._duration += 1

	def __str__(self):
		return f"ApplianceConstraints(minPower={self.minPower}, maxPower={self.maxPower})"

class OpenHEMSNode:
	"""
	Represent device of home network
	"""
	MAXNUM_CONTROLED_POWER_VALUES = 256
	def setId(self, haId):
		"""
		Set Home-Assistant id
		"""
		self.name = haId
		self.id = haId.strip().replace(" ", "_")

	def __init__(self, nameId, currentPower, maxPower, isOnFeeder=None,
			  controlledPowerFeeder=None, controlledPowerValues=None, network=None, constraints=None):
		self.id = ""
		self.setId(nameId)
		self.network = network
		self._controlledPower = controlledPowerFeeder
		self._controlledPowerValues = controlledPowerValues
		self._initControlledPowerValues()
		self.currentPower:Feeder = currentPower
		self.maxPower : Feeder = maxPower
		self._isOn : Feeder = isOnFeeder
		self.previousPower = deque()
		self._isActivate = True
		try: # Test if currentPower is well configured
			self.getCurrentPower()
		except TypeError as e:
			raise ConfigurationException(str(e)) from e
		self.constraints = constraints

	def _initControlledPowerValues(self):
		"""
		Allow to define controlledPowerValues as
		- {range: [0, 10], step: 2}
		- {0: 0, 1: 100, 2: 400, 3: 1000}
		- [0, 1, 2, 3, 4, 5]
		"""
		if isinstance(self._controlledPowerValues, list):
			values = [None for _ in self._controlledPowerValues]
			self._controlledPowerValues = dict(zip(self._controlledPowerValues, values))
		elif isinstance(self._controlledPowerValues, dict):
			myrange = None
			step = None
			controlledPowerValues = {}
			for k, v in self._controlledPowerValues.items():
				if k=="range":
					myrange=v
				elif k=="step":
					step=v
				else:
					controlledPowerValues[k]=v
			if (myrange is not None or step is not None) \
					or len(controlledPowerValues)==0:
				if step is None:
					step=1
				if myrange is None:
					myrange=[0,self.getMaxPower()]
				elif isinstance(myrange, str):
					myrange = CastUtililty.toTypeList(myrange)
				keys = range(myrange[0], myrange[1], step)
				values = [None for _ in keys]
				controlledPowerValues = controlledPowerValues | dict(zip(keys, values))
			self._controlledPowerValues = OrderedDict(sorted(controlledPowerValues))

	def _setCurrentPower(self, currentPower):
		"""
		Set current power.
		"""
		if len(self.previousPower)>=CYCLE_HISTORY:
			self.previousPower.popleft()
		self.previousPower.append(self.currentPower)
		self.currentPower = currentPower

	def getCurrentPower(self):
		"""
		Get current power 
		"""
		currentPower = self.currentPower.getValue()
		if currentPower is None or not isinstance(currentPower, (int, float)):
			errorMsg = (f"Invalid currentPower ({currentPower}) for node '{self.id}'. "
			   "Usual causes are Home-Assistant service is not ready (restart latter),"
			   " or it is a wrong configuration.")
			logger.error(errorMsg)
			raise TypeError(errorMsg)
		if self.isSwitchable() and currentPower!=0 and not self.isOn():
			logger.warning("'%s' is off but current power=%d", self.id, currentPower)
		logger.info("OpenHEMSNode.getCurrentPower(%s) = %s", self.id, currentPower)
		return currentPower

	def getMaxPower(self):
		"""
		Get max power 
		"""
		return self.maxPower.getValue()

	def _estimateNextPower(self):
		"""
		Estimate what could be the next value of currentPower if there is no change

		This function would like to know if there is a constant
		 growing/decreasing value or a random one or oscilating one...
		:return list[int]: [minValue, bestBet, maxValue]
		"""
		p0 = self.currentPower
		maxi = len(self.previousPower)
		summ = 0
		lastDiff = 0
		maxDiff = 0
		for i in reversed(range(0, maxi)):
			p1 = self.previousPower[i]
			diff = p1-p0
			if i==maxi:
				lastDiff = diff
			maxDiff = max(maxDiff, abs(diff))
			summ += diff
			p0 = p1
		avgDiff = summ/maxi
		if avgDiff>0 and lastDiff>2*avgDiff \
				or avgDiff<0 and lastDiff<2*avgDiff:
			curDiff = lastDiff
		else:
			curDiff = avgDiff
		return [self.currentPower-abs(maxDiff),\
			self.currentPower+curDiff,\
			self.currentPower+abs(maxDiff)]

	def isControlledPower(self):
		"""
			Return true if this OpenHEMSNode can be switch on/off.
		"""
		return self._controlledPower is not None

	def getControlledPowerValues(self):
		"""
		Get a dict matching possible command with possible power.
		"""
		if self._controlledPower is not None: # Fist call, init values
			return self._controlledPowerValues
		return None


	def getControlledPower(self):
		"""
		Get current wanted controlled power for node with controlable power.
		!!! Warning maybe we don't get power but an abstract value (like power from 0 to 6). !!!
		"""
		if self._controlledPower is not None:
			value = self._controlledPower.getValue()
			power = self._controlledPowerValues.get(value)
			newValue = self.getCurrentPower()
			if power is None:
				self._controlledPowerValues[value] = newValue
			elif newValue!=value: # Choice the most coherent value
				# pylint: disable=protected-access
				linkPrev, linkNext, _ = self._controlledPowerValues._OrderedDict__map[value]
				prevValue = self._controlledPowerValues[linkPrev[2]]
				nextValue = self._controlledPowerValues[linkNext[2]]
				# check that power values are ordered (like control value)
				coherent = prevValue<value<nextValue
				coherentNew = prevValue<newValue<nextValue
				if coherent and coherentNew:
					old = max(value-prevValue, nextValue-value)
					new = max(newValue-prevValue, nextValue-newValue)
					if new<old:
						self._controlledPowerValues[value] = newValue
					# else nothing to do, that was the "best"
				elif coherent:
					pass
				elif coherentNew:
					self._controlledPowerValues[value] = newValue
				# else: uncoherent values, the error is probably elsewhere
			return value
		return None

	def setControlledPower(self, power):
		"""
		Set wanted controlled power for node with controlable power.
		!!! Warning maybe we don't set power but an abstract value. !!!
		"""
		if self._controlledPower is not None:
			return self._controlledPower.setValue(power)
		return None

	def setActivate(self, value:bool):
		"""
		Used to inhibate node when it is risking over-load electrical network.
		"""
		self._isActivate = value

	def isActivate(self):
		"""
		:return bool: False if node is deactivate due to risk of over-load 
		 electrical network if we switch on it.
		"""
		return self._isActivate

	def isSwitchable(self):
		"""
			Return true if this OpenHEMSNode can be switch on/off.
		"""
		return self._isOn is not None

	def isOn(self):
		"""
		Return true if the node is not switchable or is switch on.
		"""
		# print("OpenHEMSNode.isOn(",self.id,")")
		if self._isOn is None:
			logger.error("'%s' unable to know if on.", self.id)
			return False
		return self._isOn.getValue()

	def switchOn(self, connect:bool, register=None) -> bool:
		"""
		May not work if it is impossible (No relay) or if it failed.

		return bool: False if fail to switchOn/switchOff
		"""
		if self.isSwitchable() and self._isActivate:
			if self.constraints is not None and not self.constraints.switch(connect):
				logger.warning("Cancel switch %s '%s' due to constraints",
					"on" if connect else "off", self.id)
				return not connect
			ok = self.network.networkUpdater.switchOn(connect, self)
			if ok and register is not None:
				self.network.server.registerDecrementTime(self, register)
			return ok
		logger.warning("Try to switchOn/Off a not switchable device : %s", self.id)
		return connect # Consider node is always on network
