"""
Represent appliance of home network: Devices consumming electricity.
"""

import datetime
from enum import Enum
from openhems.modules.web import OpenHEMSSchedule
from openhems.modules.util import (
	ConfigurationException, HoursRanges, Recorder
)
from .feeder import Feeder, FakeSwitchFeeder
from .node import OpenHEMSNode

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

class OutNode(OpenHEMSNode):
	"""
	Electricity consumer (like washing-machine, water-heater) that we can't switch on/off.
	We can just know if it has a power consumption. We deduce from it if it's on or off.
	This is usefull for appliances not switchable by home automation but wich can consum a lot.
	This is to take care of their max consumption in OpenHEMSServer.check() to avoid over-load.
	"""
	def __init__(self, nameId, currentPower, maxPower, network=None, nbCycleWithoutPowerForOff=0):
		isOn = GuessIsOnFeeder(self, nbCycleWithoutPowerForOff)
		super().__init__(nameId, currentPower, maxPower, network=network, isOnFeeder=isOn)

	def isSwitchable(self):
		return False

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
	def __init__(self, node, isOnFeeder=None, strategyId=None, priority=50):
		if isOnFeeder is None:
			raise ConfigurationException("Declare a Switch() but without seting isOn.")
		super(OutNode, self).__init__(node.name, node._currentPower, node._maxPower,
								isOnFeeder=isOnFeeder, network=node.network)
		self.schedule = OpenHEMSSchedule(self.id, self.name, self)
		if strategyId is None:
			strategyId = self.network.getDefaultStrategy().id
		self.strategyId = strategyId
		self._priority = priority

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

class FeedbackSwitch(Switch):
	"""
	Electricity consumer (hotwater tank, pump)
	wich are controled by a sensor.

	:param direction: Direction.UP if the sensor is increasing
		when the device is on, Direction.DOWN if decreasing
	"""
	class Mode(Enum):
		"""
		Represent recording mode of the FeedbackSwitch
		"""
		EVAL = 1 # Evaluate the parameters
		RUN = 2 # Standard run mode
		ON = 3 # Device is on and try to reach a target: Evaluate it
		OFF = 4 # Device is off and record the behavior Evaluate it

	class Direction(Enum):
		"""
		Represent the direction in witch the sensor value is going when the device is on
		"""
		UP = 1
		DOWN = -1
		TWICE = 0 # case available : TODO

	class MinMax():
		"""
		minmax tuple but need operators gt/lt for use in HoursRanges
		"""
		def __init__(self, mymin, mymax, direction=None):
			"""
			:param mymin: min value of the sensor
			:param mymax: max value of the sensor
			:param direction: Direction.UP if the sensor is increasing
				when the device is on, Direction.DOWN if decreasing
			"""
			assert mymin<mymax
			self.min = mymin
			self.max = mymax
			if direction is None:
				direction = FeedbackSwitch.Direction.UP
			self._direction = direction

		def __gt__(self, other):
			return self.min>other.min if self._direction==FeedbackSwitch.Direction.UP else self.max<other.max

		def __lt__(self, other):
			return self.min<other.min if self._direction==FeedbackSwitch.Direction.UP else self.max>other.max

	DEFAULT_MAX = 2**32 # Default max value of the sensor
	DEFAULT_MIN = -2**32 # Default min value of the sensor

	def __init__(self, switch:Switch,
			sensorFeeder=None, targeter=None, direction:Direction=Direction.UP, tablename="FeedbackSwitch"):
		"""
		:param targeter HoursRanges: Define min/max range of sensor target.
			Should be a HoursRanges with tuple (min/max) sit in place of cost.
		TODO : direction=Direction.TWICE when the sensor can increase
		 	 or decrease value when the device is on.
		"""
		if sensorFeeder is None:
			raise ConfigurationException("Declare a FeedbackSwitch() but without seting sensor.")
		super().__init__(switch,
			isOnFeeder=switch._isOn, strategyId=switch.strategyId, priority=switch._priority)
		if targeter is None:
			minmax = FeedbackSwitch.MinMax(
				FeedbackSwitch.DEFAULT_MIN, FeedbackSwitch.DEFAULT_MAX, direction)
			targeter = HoursRanges(outRangeCost=minmax)
		elif isinstance(targeter, tuple):
			minmax = FeedbackSwitch.MinMax(targeter[0],targeter[1], direction)
			targeter = HoursRanges(outRangeCost=minmax)
		elif isinstance(targeter, (float, int)):
			targeter = HoursRanges(outRangeCost=targeter)
		elif not isinstance(targeter, HoursRanges):
			raise ConfigurationException(
				"targeter should be a HoursRanges(of tuple) or tuple of 2 int or int.")
		self._targeter:HoursRanges = targeter
		self._sensor:Feeder = sensorFeeder
		# Offpeak and wanted taget can change during the day. This allow to wait for the next range
		self._rangeEnd = datetime.datetime(2024, 5, 28) # First commit date ;)
		self.minmax = None # The required min/max value.
		self.min = None # Current min value. Should be in [self.minmax.min; self.minmax.max[
		self.max = None # Current max value. Should be in ]self.minmax.min; self.minmax.max]
		# Represent the direction in witch the sensor value is going when the device is on
		self._direction:FeedbackSwitch.Direction = direction
		# Variables to store the sensor value (To eval caracteristics)
		self.mode = FeedbackSwitch.Mode.EVAL # Mode used to evaluate the characterisctics.
		self._recorder = Recorder(tablename)
		self._wasOn = False

	def __del__(self):
		self._recorder.close()

	def record(self, sensorValue):
		"""
		Record the sensor value in a database. Used to evaluate the FeedbackSwitch capacities.
		:param sensorValue: value of the sensor
		"""
		self._recorder.record(sensorValue)

	def switchOn(self, connect, register=None):
		"""
		Switch on the device. Add a registration (to get devices caracteristics).
		"""
		if self.mode!=FeedbackSwitch.Mode.RUN and self._wasOn!=connect:
			sensorValue = self._sensor.getValue()
			self.record(sensorValue)
			self._wasOn = connect
			if self.mode==FeedbackSwitch.Mode.ON and not connect  \
					or self.mode==FeedbackSwitch.Mode.OFF and connect:
				# It was one (or 2 if on/off) shot
				self.mode = FeedbackSwitch.Mode.RUN
			else:
				step = "ON" if connect else "OFF"
				self._recorder.newStep(self.id, step)
				self.record(sensorValue)
		super().switchOn(connect, register)
		return True

	def check(self) -> bool:
		"""
		Function to check if we should swith on/off the device. Should be called at each loop.

		:return: True if we switch on successfully the device false else
		TODO set a level in constraints to avoid break device:
			exp: duration<minDurationOn but sensorValue>self.minmax.max
		"""
		sensorValue = self._sensor.getValue()
		if self.mode != FeedbackSwitch.Mode.RUN:
			self.record(sensorValue)
		now = self.network.server.getTime()
		if now>self._rangeEnd:
			self.defineOptimums()
		retValue = False
		if sensorValue>self.max:
			retValue = self.switchOn(self._direction==FeedbackSwitch.Direction.DOWN)
			retValue = retValue and self._direction==FeedbackSwitch.Direction.DOWN
		elif sensorValue<self.min:
			retValue = self.switchOn(self._direction==FeedbackSwitch.Direction.UP)
			retValue = retValue and self._direction==FeedbackSwitch.Direction.UP
		return retValue

	def decrementTime(self, time:int=0) -> bool:
		"""
		Decrease time of schedule and return remaining time.
		"""
		del time
		self.check()
		return 0


	def isScheduled(self):
		return False

	def getMinMaxRange(self):
		"""
		:return: minmax range of the sensor for current time-slot
		"""
		return self.minmax

	def setMinMaxRange(self, mymin=None, mymax=None):
		"""
		:return: minmax range of the sensor for current time-slot
		"""
		if mymin is not None:
			assert self.minmax.min<=mymin<self.minmax.max
			self.min = mymin
		if mymax is not None:
			assert self.minmax.min<mymax<=self.minmax.max
			self.max = mymax

	def setLowestMinMax(self):
		"""
		Set target to use the minimum amount of energy.
		"""
		if self._direction==FeedbackSwitch.Direction.UP:
			self.setMinMaxRange(self.minmax.min, self.minmax.min + 1)
		else:
			self.setMinMaxRange(self.minmax.max - 1, self.minmax.max)

	def setEndToReach(self, mymin, mymax):
		"""
		Set target to use the maximum amount of energy to preserve next range.
		"""
		if self._direction==FeedbackSwitch.Direction.UP:
			self.getTimeToReach(self.min, mymin)
		else:
			self.getTimeToReach(self.max, mymax)

	def defineOptimums(self):
		"""
		define min/max and rangeEnd according to min/max allowed and strategy.
		"""
		now = self.network.server.getTime()
		_, self._rangeEnd, self.minmax = self._targeter.checkRange(now)
		if isinstance(self.minmax, (float, int)):
			if self._direction==FeedbackSwitch.Direction.UP:
				mymin = self.minmax
				mymax = FeedbackSwitch.DEFAULT_MAX
			else: # if self._direction==FeedbackSwitch.Direction.DOWN:
				mymin = FeedbackSwitch.DEFAULT_MIN
				mymax = self.minmax
			self.minmax = FeedbackSwitch.MinMax(mymin, mymax, self._direction)
		self.min = self.minmax.min
		self.max = self.minmax.max
		prices = self.network.getHoursRanges()
		if prices is not None and not prices.isEmpty():
			_, rangeEnd, cost = prices.checkRange(now)
			self._rangeEnd = min(rangeEnd, self._rangeEnd)
			mynext = now + datetime.timedelta(seconds=10)
			_, _, nextCost = prices.checkRange(mynext)
			if cost<nextCost: # Should switch on on this range
				self.setLowestMinMax()
				self.defineOptimumTarget4RangeEnd(cost, nextCost)

	def defineOptimumTarget4RangeEnd(self, cost, nextCost):
		"""
		Set target to use the maximum amount of energy to preserve next range.
		Default for just offpeak strategy.
		"""
		del cost, nextCost
		if self._direction==FeedbackSwitch.Direction.UP:
			self.setEndToReach(self.minmax.max - 1, self.minmax.max)
		else:
			self.setEndToReach(self.minmax.min, self.minmax.min + 1)

	def getTimeToReach(self, fromValue, toValue):
		"""
		Estimate time to switchOn device to go from fromValue to toValue.
		Use statistics
		"""
		del fromValue, toValue
		# TODO
		return 0

	def __str__(self):
		return (f"FeedbackSwitch(name={self.name}, strategy={self.strategyId}, priority={self._priority}"
			f" currentPower={self._currentPower}, maxPower={self._maxPower}, isOn={self.isOn()},"
			f" sensor={self._sensor}, targeter={self._targeter}, constraints={self._constraints})")

class HeatingSystem(FeedbackSwitch):
	"""
	Electricity consumer (like heater, fridge, hotwater tank)
	wich are controled by a sensor.
	"""
	def __init__(self, node:FeedbackSwitch):
		super().__init__(node,
			sensorFeeder=node._sensor, targeter=node._targeter, direction=node._direction,
			tablename="HeatingSystem")

	def __str__(self):
		return (f"HeatingSystem(name={self.name}, strategy={self.strategyId}, priority={self._priority}"
			f" currentPower={self._currentPower}, maxPower={self._maxPower}, isOn={self.isOn()},"
			f" sensor={self._sensor}, targeter={self._targeter}, constraints={self._constraints})")
