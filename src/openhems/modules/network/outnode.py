"""
Represent device of home network
"""

import logging
import datetime
from openhems.modules.web import OpenHEMSSchedule
from openhems.modules.util import ConfigurationException, HoursRanges
from .feeder import Feeder
from .node import OpenHEMSNode
import sqlite3

class GuessIsOnFeeder(Feeder):
	"""
	Guess if node is on with currentPower.
	"""
	def __init__(self, source, nbCycleWithoutPowerForOff=1):
		"""
		:param source: The node source of power with network.getCycleId() and getCurrentPower().
		:param nbCycleWithoutPowerForOff: number of cycle without power before we consider the device is off
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
		return f"GuessIsOnFeeder(isOn={self.getValue()}, nbCycleWithoutPowerForOff={self.nbCycleWithoutPowerForOff})"

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

	def __str__(self):
		return (f"OutNode(name={self.name}, currentPower={self.currentPower},"
			f"maxPower={self.maxPower}, isOn={self.isOn()})")

	def __repr__(self):
		return str(self)

class Switch(OutNode):
	"""
	Electricity consumer (like washing-machine, water-heater)
	wich can be switch on/off.
	"""
	def __init__(self, nameId, strategyId, currentPower, maxPower, isOnFeeder=None,
			priority=50, network=None, constraints=None):
		if isOnFeeder is None:
			raise ConfigurationException("Declare a Switch() but without seting isOn.")
		super(OutNode, self).__init__(nameId, currentPower, maxPower, isOnFeeder=isOnFeeder, network=network)
		self.schedule = OpenHEMSSchedule(self.id, nameId, self)
		self.strategyId = strategyId
		self._priority = priority
		self._constraints = constraints

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

	def getConstraints(self):
		"""
		Return schedule
		"""
		return self._constraints

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
		constraints = self.getConstraints()
		if constraints is not None:
			return constraints.decrementTime(time)
		return 0

	def getStrategyId(self):
		"""
		Return StrategyId
		"""
		return self.strategyId

	def __str__(self):
		return (f"Switch(name={self.name}, strategy={self.strategyId}, priority={self._priority}"
			f" currentPower={self.currentPower},"
			f"maxPower={self.maxPower}, isOn={self.isOn()})")

class FeedbackSwitchMinMax():
	"""
	Electricity consumer (like heater, fridge, hotwater tank)
	"""
	def __init__(self, min, max, direction=1):
		"""
		:param min: min value of the sensor
		:param max: max value of the sensor
		:param direction: 1 if the sensor is increasing when the device is on, -1 if decreasing
		"""
		assert(min<max)
		self.min = min
		self.max = max
		self.direction = direction

	def __gt__(self, other):
		return self.min>other.min if self.direction>0 else self.max<other.max
	def __lt__(self, other):
		return self.min<other.min if self.direction>0 else self.max>other.max

class Recorder():
	"""
	Recorder of a sensor value.
	"""
	_INSTANCE = None
	@staticmethod
	def getInstance():
		"""
		Static access method.
		"""
		if Recorder._INSTANCE is None:
			Recorder._INSTANCE = Recorder()
		return Recorder._INSTANCE

	def __init__(self, tablename=None, step=None):
		self._recordTimeStart = datetime.datetime.now()
		self.con = sqlite3.connect("openhems.db")
		self.step = step
		if tablename is not None:
			self.cur = self.con.cursor()
			self.tablename = tablename
			self.cur.execute(f"Create table if not exists {tablename} ("
				"i integer primary key,"
				"deviceId text,"
				"stepType text, step text,"
				"ts timestamp,"
				"value number(10))"
			)

	def setStep(self, deviceId, stepType, step):
		"""
		Set the step of the recorder.
		"""
		self.deviceId = deviceId
		self.stepType = stepType
		self.step = step
	
	def record(self, value):
		"""
		Record the sensor value in a database.
		"""
		if self.step is not None:
			self.cur.execute(f"Insert into {self.tablename} (deviceId, stepType, step, ts, value)"
					"values (?, ?, ?, ?, ?)",
				(self.deviceId, self.stepType, self.step, datetime.datetime.now(), value))
			self.con.commit()

class FeedbackSwitch(Switch):
	"""
	Electricity consumer (hotwater tank, pump)
	wich are controled by a sensor.

	:param direction: 1 if the sensor is increasing when the device is on, -1 if decreasing
	"""
	class Mode:
		EVAL = 1 # Evaluate the parameters
		RUN = 2 # Standard run mode
		ON = 3 # Device is on and try to reach a target: Evaluate it
		OFF = 4 # Device is off and record the behavior Evaluate it

	def __init__(self, nameId, strategyId, currentPower, maxPower, isOnFeeder=None,
			priority=50, network=None, sensorFeeder=None, targeter=None, direction:int=1, applianceConstraints:ApplianceConstraints=None):
		"""
		:param targeter HoursRanges: Define min/max range of sensor target. Should be a HoursRanges with tuple (min/max) sit in place of cost.
		TODO : direction=0 when the sensor can increase or decrease value when the device is on.
		"""
		if sensorFeeder is None:
			raise ConfigurationException("Declare a FeedbackSwitch() but without seting sensor.")
		super().__init__(self, nameId, strategyId, currentPower, maxPower, isOnFeeder=isOnFeeder,
			priority=priority, network=network)
		if targeter is None:
			targeter = HoursRanges(outRangeCost=FeedbackSwitchMinMax(-2**32,2**32, direction))
		elif isinstance(targeter, tuple):
			minmax = FeedbackSwitchMinMax(targeter[0],targeter[1], direction)
			targeter = HoursRanges(outRangeCost=targeter)
		elif isinstance(targeter, int):
			minmax = FeedbackSwitchMinMax(targeter, 2**32, direction) if direction>0 else FeedbackSwitchMinMax(-2**32, targeter, direction)
			targeter = HoursRanges(outRangeCost=minmax)
		elif not isinstance(targeter, HoursRanges):
			raise ConfigurationException("targeter should be a HoursRanges(of tuple) or tuple of 2 int or int.")
		self.targeter:HoursRanges = targeter
		self.sensor:Feeder = sensorFeeder
		now = self.network.server.getTime()
		_, self.rangeEnd, self.minmax = self.targeter.checkRange(now)
		self.min = self.minmax.min # Current min value. Should be in [self.minmax.min; self.minmax.max[
		self.max = self.minmax.max # Current max value. Should be in ]self.minmax.min; self.minmax.max]
		self.direction = direction
		self.mode = FeedbackSwitch.Mode.EVAL # Mode used to evaluate the characterisctics.
		self._recorder = Recorder("FeedbackSwitch")
		self._isOn = False
		self._stepId = 0

	def record(self, sensorValue):
		"""
		"""
		self._recorder.record(sensorValue)
		pass

	def switchOn(self, on):
		"""
		Switch on the device.
		"""
		if self.mode!=FeedbackSwitch.Mode.RUN and self._isOn!=on:
			sensorValue = self.sensor.getValue()
			self.record(sensorValue)
			self._isOn = on
			if self.mode==FeedbackSwitch.Mode.ON and not on  \
					or self.mode==FeedbackSwitch.Mode.OFF and on:
				# It was one (or 2 if on/off) shot
				self.mode = FeedbackSwitch.Mode.RUN
			else:
				step = "ON" if on else "OFF"
				self._stepId += 1
				self._recorder.setStep(self.id, step, "switchOn_"+self.stepId)
				self.record(sensorValue)
		super().switchOn(on)
		return True

	def check(self) -> bool:
		"""
		Function to check if we should swith on/off the device. Should be called at each loop.

		:return: True if we switch on successfully the device false else
		TODO set a level in constraints to avoid break device:
			exp: duration<minDurationOn but sensorValue>self.minmax.max
		"""
		sensorValue = self.sensor.getValue()
		if self.mode != FeedbackSwitch.Mode.RUN:
			self.record(sensorValue)
		if sensorValue>self.max:
			retValue = self.switchOn(self.direction<0) and self.direction<0
		elif sensorValue<self.min:
			retValue = self.switchOn(self.direction>0) and self.direction>0
		if self.network.server.getTime()>self.rangeEnd:
			self.defineOptimums()
		return retValue

	def isScheduled(self):
		return False

	def getMinMaxRange(self):
		"""
		:return: minmax range of the sensor for current time-slot
		"""
		return self.minmax

	def setMinMaxRange(self, min=None, max=None):
		"""
		:return: minmax range of the sensor for current time-slot
		"""
		if min is not None:
			assert(self.minmax.min<=min<self.minmax.max)
			self.min = min
		if max is not None:
			assert(self.minmax.min<max<=self.minmax.max)
			self.max = max

	def setLowestMinMax(self):
		"""
		Set target to use the minimum amount of energy.
		"""
		if self.direction>0:
			self.setMinMaxRange(self.minmax.min, self.minmax.min + 1)
		else:
			self.setMinMaxRange(self.minmax.max - 1, self.minmax.max)

	def setEndToReach(self, min, max):
		"""
		Set target to use the maximum amount of energy to preserve next range.
		"""
		if self.direction>0:
			self.getTimeToReach(self.min, min)
		else:
			self.getTimeToReach(self.max, max)

	def defineOptimums(self):
		"""
		define min/max and rangeEnd according to min/max allowed and strategy.
		"""
		now = self.network.server.getTime()
		_, self.rangeEnd, self.minmax = self.targeter.checkRange(now)
		self.min = self.minmax.min
		self.max = self.minmax.max
		prices = self.network.getHoursRanges()
		if prices is not None and not prices.isEmpty():
			_, rangeEnd, cost = prices.checkRange(now)
			if rangeEnd<self.rangeEnd:
				self.rangeEnd = rangeEnd
			next = now + datetime.timedelta(seconds=self.network.server.loopDelay)
			_, _, nextCost = prices.checkRange(next)
			if cost<nextCost: # Should switch on on this range
				self.setLowestMinMax(self)
				self.defineOptimumTarget4RangeEnd(cost, nextCost)

	def defineOptimumTarget4RangeEnd(self, cost, nextCost):
		"""
		Set target to use the maximum amount of energy to preserve next range.
		Default for just offpeak strategy.
		"""
		if self.direction>0:
			self.setEndToReach(self.minmax.max - 1, self.minmax.max)
		else:
			self.setEndToReach(self.minmax.min, self.minmax.min + 1)

	def getTimeToReach(self, fromValue, toValue):
		"""
		Estimate time to switchOn device to go from fromValue to toValue.
		Use statistics
		"""
		# TODO
		pass
		return 0

class HeaterCooler(FeedbackSwitch):
	"""
	Electricity consumer (like heater, fridge, hotwater tank)
	wich are controled by a sensor.
	"""
	def __init__(self, nameId, strategyId, currentPower, maxPower, isOnFeeder=None,
			priority=50, network=None, sensorFeeder=None, targeter=None):
		super().__init__(nameId, strategyId, currentPower, maxPower,
			isOnFeeder=isOnFeeder, priority=priority,
			network=network, sensorFeeder=sensorFeeder,
			targeter=targeter)