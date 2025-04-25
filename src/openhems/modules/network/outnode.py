"""
Represent appliance of home network: Devices consumming electricity.
"""

import datetime
from enum import Enum
import logging
import numpy as np
from openhems.modules.web import OpenHEMSSchedule
from openhems.modules.util import (
	ConfigurationException, HoursRanges, Recorder
)
from .feeder import Feeder, FakeSwitchFeeder
from .node import OpenHEMSNode

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

class TimeModelization:
	"""
	This is the most simple modelization of the feeedbackSensor.
	We use a polynomial regression from numpy (No IA nor genetics).
	The X is the time, Y is the sensor value. But 
	- All don't start at the same sensor value. So readjust it.
	- It doesn't take in account the latency at the begenning/end
	- It would be better to set time in X (for possibly duplicate sensor value (like boiling water))
	but this would be more difficult to do the reverse for getTime().
	"""
	def __init__(self):
		self._model = {}
		self._datas = {}
		self._degree = 1
		self._tmp = {}

	def plot(self, step):
		"""
		Display a popup with the curve. Usefull for manual DEBUG (And for demo ;) ).
		"""
		# pylint: disable=import-outside-toplevel
		import matplotlib.pyplot as plt # because not used on prod
		axes = plt.axes()
		axes.grid()
		plt.xlabel('Time')
		plt.ylabel('Sensor value')
		plt.scatter(self._datas[step][0], self._datas[step][1])
		mymin = min(self._datas[step][0])*0.9
		mymax = max(self._datas[step][0])*1.1
		xp = np.linspace(mymin, mymax, 100)
		plt.plot(xp, self.applyModel(step, xp), c='r')
		plt.show()

	def applyModel(self, step, x, model=None):
		"""
		Function 'reverse' of generateModel()
		"""
		if model is None:
			model = self._model[step]
		value = 0
		degree = len(model)
		for deg,coef in enumerate(model):
			p = degree-deg
			xVals = pow(x, p)
			# print("applyModel() : ",coef," x ",x,"^",p)
			value += coef * xVals
		# print("applyModel(",step,",",x,") : ",value)
		return value

	def getCost(self, step, model):
		"""
		:return: an abstract number representing the cost of a model choice
		Use the square distance. Greater is the number, worst is the model.
		But too hight is not so good if it reproduce source datas errors.
		"""
		cost = 0
		datas = self._datas[step]
		for i,x in enumerate(datas[0]): # For all X
			y0 = self.applyModel("", x, model=model)
			y1 = datas[1][i]
			cost += pow(y0-y1, 2)
		logger.debug("getCost(%s, %s) : %s", step, model, cost)
		return cost

	def generateModel(self, step):
		"""
		Here it is a polynomial regression.
		https://mrmint.fr/regression-polynomiale

		:degree: The degree of final polynom
		"""
		lowestCost = 2**32
		for degree in range(1, 5):
			model = np.poly1d(np.polyfit(self._datas[step][0], self._datas[step][1], degree))
			cost = self.getCost(step, model)
			if cost<lowestCost:
				self._degree = degree
				self._model[step] = model
				lowestCost = cost
		# TODO : Check for greater _degree if they better fit datas
		logger.debug("Model : %s", self._model[step])
		# For DEBUG but mannually self.plot(step)

	def _storeRecord(self, recordList):
		"""
		Store a record. But as a record not always start from the same sensor value,
		we don't always start at '0'.
		"""
		datasX = []
		datasY = []
		timeStart = recordList[0][0]
		deltaTime = 0
		# Find the "time" i.e. the i to start from.
		closestDist = 2**32
		value0 = recordList[0][1]
		for value1,timeStart1 in self._tmp.items():
			dist = pow(value1-value0, 2)
			if dist<closestDist:
				deltaTime=timeStart1-timeStart
				# print("deltaTime:",deltaTime, dist, " for value=",value0)
				closestDist=dist

		for time,value in recordList:
			time += deltaTime
			if self._tmp.get(value) is None:
				self._tmp[value] = time
			datasX.append(time)
			datasY.append(value)
		# print("DatasX : ", datasX); print("DatasY : ", datasY)
		return datasX, datasY

	def storeDatas(self, step, datas):
		"""
		try remove some latency?
		Exp datas = [ [(0,0),(1,1),(2,2)],
					  [(0,1),(1,2),(2, 3),(3,3.5)]]
		"""
		datasX = []
		datasY = []
		firstRecord = datas[0]
		first = firstRecord[0][1]
		last = firstRecord[len(firstRecord)-1][1]
		self._tmp = {}
		if first<last:# Growing list
			# print("growing list")
			datas.sort(key=lambda x: x[0][1]) # Sort record list by first sensor value
		else: # going down list
			# print("descending list")
			datas.sort(reverse=True, key=lambda x: x[0][1]) # Sort record list by first sensor value
		for recordList in datas:
			dx, dy = self._storeRecord(recordList)
			datasX += dx
			datasY += dy
		logger.debug("DatasX : %s", datasX)
		logger.debug("DatasY : %s", datasY)
		self._datas[step] = (datasY, datasX)

# class SpeedModelization:
# 	"""
# 	The X is the sensor value, Y is the slope of the function wich give the time
# 	(Skip first, ignore latency).
# 	TODO
# 	"""

class FeedbackModelizer:
	"""
	The goal is to be able to predict futur value of the sensor in function the device is on/off.
	"""
	EVAL_NUM_CYCLES = 4
	class Mode(Enum):
		"""
		Represent recording mode of the FeedbackSwitch
		"""
		EVAL = 1 # Evaluate the parameters
		RUN = 2 # Standard run mode
		ON = 3 # Device is on and try to reach a target: Evaluate it
		OFF = 4 # Device is off and record the behavior Evaluate it

	def __init__(self, switch, tablename):
		self._mode = FeedbackModelizer.Mode.EVAL # Mode used to evaluate the characterisctics.
		self._recorder:Recorder = Recorder(tablename)
		self._wasOn:bool = switch.isOn()
		self.node:OpenHEMSNode = switch
		self._model:TimeModelization = TimeModelization()

	def __del__(self):
		self._recorder.close()

	def getMode(self) -> Mode:
		"""
		:return: the current mode of the modelizer.
		"""
		return self._mode

	def record(self, sensorValue, now=None):
		"""
		Record the sensor value in a database. Used to evaluate the FeedbackSwitch capacities.

		:param sensorValue: value of the sensor
		"""
		if self._mode != FeedbackModelizer.Mode.RUN:
			if now is None:
				now = self.node.network.server.getTime()
			self._recorder.record(sensorValue, now)

	def switch(self, connect):
		"""
		Switch on the device. Add a registration (to get devices caracteristics).
		"""
		if self._mode!=FeedbackModelizer.Mode.RUN and self._wasOn!=connect:
			sensorValue = self.node.getSensorValue()
			self.record(sensorValue)
			self._wasOn = connect
			# Determine if we stop EVAL
			match self._mode:
				case FeedbackModelizer.Mode.ON:
					ok = not connect # It was one (or 2 if on/off) shot
				case FeedbackModelizer.Mode.OFF:
					ok = connect # It was one (or 2 if on/off) shot
				case FeedbackModelizer.Mode.EVAL:
					ok = self._recorder.getId()>=self.EVAL_NUM_CYCLES
				case _:
					ok = False
			if ok: # stop EVAL
				logger.info("FeedbackModelizer : DB trace : inactivation, use Mode.RUN")
				if self._mode==FeedbackModelizer.Mode.EVAL:
					logger.info("FeedbackModelizer : DB trace : analyze datas")
					self.analyzeDatas()
				self._mode = FeedbackModelizer.Mode.RUN
			else: # self._mode==FeedbackModelizer.Mode.EVAL
				step = "ON" if connect else "OFF"
				logger.info("FeedbackModelizer : DB trace : new step '%s' (%s)", step, self._recorder.getId())
				self._recorder.newStep(self.node.id, step)
				self.record(sensorValue)

	def getTimeToReach(self, fromValue:float, toValue:float) -> float:
		"""
		Estimate time to switchOn device to go from fromValue to toValue.
		Use statistics

		:fromValue float: Value of the sensor at the begenning
		:toValue float: Value of the sensor at the end
		:return: time in seconds
		"""
		if fromValue==toValue:
			return 0
		step = "ON" if fromValue<toValue else "OFF"
		t0 = self._model.applyModel(step, fromValue)
		t1 = self._model.applyModel(step, toValue)
		return t1-t0

	def analyzeDatas(self):
		"""
		Difficult part ;)
		"""
		for step in ["ON", "OFF"]:
			datas = self._recorder.getDatas(self.node.id, step)
			# print(datas)
			self._model.storeDatas(step, datas)
			self._model.generateModel(step)

class FeedbackSwitch(Switch):
	"""
	Electricity consumer (hotwater tank, pump)
	wich are controled by a sensor.

	:param direction: Direction.UP if the sensor is increasing
		when the device is on, Direction.DOWN if decreasing
	"""
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
		def __str__(self):
			return f"MinMax({self.min},{self.max})"

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
		self._minmax = None # The required min/max value.
		self._min = None # Current min value. Should be in [self._minmax.min; self._minmax.max[
		self._max = None # Current max value. Should be in ]self._minmax.min; self._minmax.max]
		# Represent the direction in witch the sensor value is going when the device is on
		self._direction:FeedbackSwitch.Direction = direction
		self._sensorMinStep = 1 # The minimal step between a min and max value
		# Variables to store the sensor value (To eval caracteristics)
		self._model = FeedbackModelizer(self, tablename)
		self._nextTargets = []


	def __del__(self):
		del self._model

	def switchOn(self, connect, register=None):
		"""
		Switch on the device. Add a registration (to get devices caracteristics).
		"""
		self._model.switch(connect)
		super().switchOn(connect, register)
		return True

	def check(self) -> bool:
		"""
		Function to check if we should swith on/off the device. Should be called at each loop.

		:return: True if we switch on successfully the device false else
		TODO set a level in constraints to avoid break device:
			exp: duration<minDurationOn but sensorValue>self._minmax.max
		"""
		sensorValue = self._sensor.getValue()
		now = self.network.server.getTime()
		self._model.record(sensorValue, now)
		self.checkTarget(now)
		if now>self._rangeEnd:
			self.defineOptimums()
		retValue = False
		if sensorValue>self._max:
			retValue = self.switchOn(self._direction==FeedbackSwitch.Direction.DOWN)
			retValue = retValue and self._direction==FeedbackSwitch.Direction.DOWN
		elif sensorValue<self._min:
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
		return self._minmax

	def setMinMaxRange(self, mymin=None, mymax=None):
		"""
		:return: minmax range of the sensor for current time-slot
		"""
		if mymin is not None:
			self._min = mymin
		if mymax is not None:
			self._max = mymax
		assert self._minmax.min<=self._min<self._max<=self._minmax.max

	def setLowestMinMax(self):
		"""
		Set target to use the minimum amount of energy.
		"""
		if self._direction==FeedbackSwitch.Direction.UP:
			self.setMinMaxRange(self._minmax.min, self._minmax.min + 1)
		else:
			self.setMinMaxRange(self._minmax.max - 1, self._minmax.max)

	def setToMin(self):
		"""
		Considering we are in a starving energy state
		"""
		if self._direction==FeedbackSwitch.Direction.UP:
			mymin = self._minmax.min
			mymax = self._minmax.min + self._sensorMinStep
		else:
			mymin = self._minmax.max - self._sensorMinStep
			mymax = self._minmax.max
		self._min = mymin
		self._max = mymax

	def setToMax(self, atEnd=True):
		"""
		Considering we are in a aboundant energy state
		Set target to use the maximum amount of energy to use it as "battery"
		 - only at range end if 'atEnd' (For offpeak) Forcing high energy always 
		 will switch on/off often the device witch could damage it.
		 - Else now (With solar panel, we don't know when it will end)
		"""
		if self._direction==FeedbackSwitch.Direction.UP:
			mymin = self._minmax.max - self._sensorMinStep
			mymax = self._minmax.max
			fromValue = mymin
			toValue = mymax
		else:
			mymin = self._minmax.min
			mymax = self._minmax.min + self._sensorMinStep
			fromValue = mymax
			toValue = mymin
		if atEnd:
			self._min = self._minmax.min
			self._max = self._minmax.max
			time = self._model.getTimeToReach(fromValue, toValue)
			time *= 1.1 # a 10% margin
			reachModeTime = self._rangeEnd - datetime.timedelta(seconds=time)
			self.addNexTarget(reachModeTime, FeedbackSwitch.MinMax(mymin, mymax))
		else:
			self._min = mymin
			self._max = mymax

	def addNexTarget(self, reachModeTime, minmax):
		"""
		Add a targeting min/max wich occured at reachModeTime
		"""
		if self.network.server.getTime()>reachModeTime:
			self._min = minmax.min
			self._max = minmax.max
		else:
			self._nextTargets.append((reachModeTime, minmax))
			# Sort by reachModeTime
			self._nextTargets.sort(key=lambda x:x[0])

	def checkTarget(self, now=None):
		"""
		Check if time elapsed and we reach a target (self._nextTargets).
		"""
		if len(self._nextTargets)>0:
			reachModeTime, minmax = self._nextTargets[0]
			if now is None:
				now = self.network.server.getTime()
			if now>reachModeTime:
				self._min = minmax.min
				self._max = minmax.max
				self._nextTargets.pop(0)



	def defineOptimums(self):
		"""
		define min/max and rangeEnd according to min/max allowed and strategy.
		"""
		now = self.network.server.getTime()
		_, self._rangeEnd, self._minmax = self._targeter.checkRange(now)
		if isinstance(self._minmax, (float, int)):
			if self._direction==FeedbackSwitch.Direction.UP:
				mymin = self._minmax
				mymax = FeedbackSwitch.DEFAULT_MAX
			else: # if self._direction==FeedbackSwitch.Direction.DOWN:
				mymin = FeedbackSwitch.DEFAULT_MIN
				mymax = self._minmax
			self._minmax = FeedbackSwitch.MinMax(mymin, mymax, self._direction)
		self._min = self._minmax.min
		self._max = self._minmax.max
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
		if cost<nextCost:
			self.setToMax()

	def __str__(self):
		return (f"FeedbackSwitch(name={self.name}, strategy={self.strategyId}, priority={self._priority}"
			f" currentPower={self._currentPower}, maxPower={self._maxPower}, isOn={self.isOn()},"
			f" sensor={self._sensor}, targeter={self._targeter}, constraints={self._constraints})")

	def getSensorValue(self):
		"""
		:return: The value of the feedback sensor.
		"""
		return self._sensor.getValue()

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
