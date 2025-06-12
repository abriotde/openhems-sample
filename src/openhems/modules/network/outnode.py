"""
Represent appliance of home network: Devices consumming electricity.
"""

import logging
from openhems.modules.web import OpenHEMSSchedule
from openhems.modules.util import ConfigurationException
from .feeder import Feeder, FakeSwitchFeeder
from .node import Node

logger = logging.getLogger(__name__)

class GuessIsOnFeeder(Feeder):
	"""
	Guess if node is on with currentPower. Usefull for not home-automationable devices.
	We can just add a connected plug.
	"""
	def __init__(self, source, nbCycleWithoutPowerForOff=1):
		"""
		:param source: The node source of power with network.getCycleId() and getCurrentPower().
		:param nbCycleWithoutPowerForOff:
			number of cycle without power before we consider the device is off
		"""
		super().__init__(source)
		self._value = source
		self._nbCycleWithoutPower = 0
		self._lastCycleId = -1
		# Number of cycle without power before we consider the device is off
		self.nbCycleWithoutPowerForOff = nbCycleWithoutPowerForOff

	def getValue(self):
		"""
		Return True if the device is on (consuming power).
		"""
		if self._value.getCurrentPower()>0:
			self._nbCycleWithoutPower = 0
			return True
		cycleId = self._value.network.getCycleId()
		if self._lastCycleId!=cycleId:
			self._nbCycleWithoutPower += 1
			self._lastCycleId=cycleId
		return self._nbCycleWithoutPower<self.nbCycleWithoutPowerForOff

	def __str__(self):
		return (f"GuessIsOnFeeder(isOn={self.getValue()},"
			f"nbCycleWithoutPowerForOff={self.nbCycleWithoutPowerForOff})")

	def __repr__(self):
		return str(self)

class OutNode(Node):
	"""
	Electricity consumer (like washing-machine, water-heater) that we can't switch on/off.
	We can just know if it has a power consumption. We deduce from it if it's on or off.
	This is usefull for appliances not switchable by home automation but wich can consum a lot.
	This is to take care of their max consumption in OpenHEMSServer.check() to avoid over-load.
	"""
	def __init__(self, nameId, currentPower, maxPower, *, network=None, nbCycleWithoutPowerForOff=0):
		isOn = GuessIsOnFeeder(self, nbCycleWithoutPowerForOff)
		super().__init__(nameId, currentPower, maxPower, network=network, isOnFeeder=isOn)

	def isSwitchable(self):
		return False

	def getFeeder(self, sourceType):
		"""
		:sourceType: Availables are "currentPower"
		"""
		if sourceType=="currentPower":
			return self._currentPower
		return super().getFeeder(sourceType)

	def setFakeSwitchFeeder(self, isOnFeeder):
		"""
		Function used in FakeNetwork.getFeeder()
		"""
		self._currentPower = FakeSwitchFeeder(self._currentPower, isOnFeeder)

	def __str__(self):
		return (f"OutNode(name={self.name}, currentPower={self._currentPower},"
			f"maxPower={self._maxPower}, isOn={self.isOn()})")

	def __repr__(self):
		return str(self)

class Switch(OutNode):
	"""
	Electricity consumer (like washing-machine, water-heater)
	wich can be switch on/off.
	"""
	def __init__(self, node, isOnFeeder=None, *, strategyId=None, priority=50):
		if isOnFeeder is None:
			raise ConfigurationException("Declare a Switch() but without seting isOn.")
		super(OutNode, self).__init__(node.name, node._currentPower, node._maxPower,
								isOnFeeder=isOnFeeder, network=node.network)
		self.schedule = OpenHEMSSchedule(self.id, self.name, self)
		if strategyId is None:
			strategyId = self.network.getDefaultStrategy().id
		self.strategyId = strategyId
		self._priority = priority

	def getFeeder(self, sourceType):
		"""
		:sourceType: Availables are "isOn", "currentPower"
		"""
		if sourceType=="isOn":
			return self._isOn
		return super().getFeeder(sourceType)

	def isSwitchable(self):
		return True

	def isOn(self):
		"""
		Return True if the device is on (consuming power).
		"""
		# useless, but as GuessIsOnFeeder could be replace by overiding isOn() method
		return super(OutNode, self).isOn()

	def getPriority(self):
		"""
		:return int: number representing the level of priority
		"""
		return self._priority

	def getSchedule(self):
		"""
		Return schedule
		"""
		return self.schedule

	def setCondition(self, condition):
		"""
		Set a condition to switchOn
		even if the node is  not manually schedule.
		"""
		self.schedule.setCondition(condition)
		return condition

	def isScheduled(self):
		"""
		Return True, if device is schedule to be on
		"""
		sch = self.getSchedule()
		if sch is not None:
			return sch.isScheduled()
		return False

	def decrementTime(self, time:int) -> int:
		"""
		Decrease time of schedule and return remaining time.
		"""
		sch = self.getSchedule()
		if sch is not None and self.isOn():
			return sch.decrementTime(time)
		return 0

	def getStrategyId(self):
		"""
		Return StrategyId
		"""
		return self.strategyId

	def __str__(self):
		return (f"Switch(name={self.name}, strategy={self.strategyId}, priority={self._priority}"
			f" currentPower={self._currentPower},"
			f"maxPower={self._maxPower}, isOn={self.isOn()})")
