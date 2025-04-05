"""
Represent device of home network
"""

import logging

from typing import Final
from collections import deque, OrderedDict
from openhems.modules.web import OpenHEMSSchedule
from openhems.modules.contract import Contract
from openhems.modules.util import CastUtililty, ConfigurationException
from .feeder import Feeder, ConstFeeder

CYCLE_HISTORY: Final[int] = 10 # Number of cycle we keep history
logger = logging.getLogger(__name__)

class OpenHEMSNode:
	"""
	Represent device of home network
	"""

	def setId(self, haId):
		"""
		Set Home-Assistant id
		"""
		self.id = haId.strip().replace(" ", "_")

	def __init__(self, nameId, currentPower, maxPower, isOnFeeder=None,
			  controlledPowerFeeder=None, controlledPowerValues=None):
		self.id = ""
		self.setId(nameId)
		self.network = None
		self._isSwitchable = False
		self._isOn:Feeder = None
		self._controlledPower = controlledPowerFeeder
		self._controlledPowerValues = controlledPowerValues
		self._initControlledPowerValues()
		self.currentPower:Feeder = currentPower
		try: # Test if currentPower is well configured
			self.getCurrentPower()
		except TypeError as e:
			raise ConfigurationException(str(e)) from e
		self.maxPower:Feeder = maxPower
		if isOnFeeder is not None:
			self._isOn = isOnFeeder
			self._isSwitchable = True
		else:
			self._isSwitchable = False
		self.previousPower = deque()
		self._isActivate = True

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
		if self._isSwitchable and currentPower!=0 and not self.isOn():
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
		!!! Warning maybe we don't get power but an abstract value. !!!
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

	def isSwitchable(self):
		"""
			Return true if this OpenHEMSNode can be switch on/off.
		"""
		return self._isSwitchable

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

	def isOn(self):
		"""
		Return true if the node is not switchable or is switch on.
		"""
		# print("OpenHEMSNode.isOn(",self.id,")")
		if self._isSwitchable:
			return self._isOn.getValue()
		return True

	def switchOn(self, connect: bool) -> bool:
		"""
		May not work if it is impossible (No relay) or if it failed.
		
		return bool: False if fail to switchOn/switchOff
		"""
		if self._isSwitchable and self._isActivate:
			return self.network.networkUpdater.switchOn(connect, self)
		logger.warning("Try to switchOn/Off a not switchable device : %s", self.id)
		return connect # Consider node is always on network

class OutNode(OpenHEMSNode):
	"""
	Electricity consumer (like washing-machine, water-heater).
	:param int priority: A device with higth priority is more important than a low priority one.
		Usually priority is a number between 0 and 100
	"""
	def __init__(self, nameId, strategyId, currentPower, maxPower, isOnFeeder=None, priority=50):
		super().__init__(nameId, currentPower, maxPower, isOnFeeder)
		self.name = nameId
		self.schedule = OpenHEMSSchedule(self.id, nameId)
		self.strategyId = strategyId
		self._priority = priority

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

	def getStrategyId(self):
		"""
		Return StrategyId
		"""
		return self.strategyId

	def __str__(self):
		return (f"OutNode(name={self.name}, strategy={self.strategyId}, priority={self._priority}"
			f" currentPower={self.currentPower},"
			f"maxPower={self.maxPower}, isOn={self._isOn})")
	def __repr__(self):
		return str(self)

class InOutNode(OpenHEMSNode):
	"""
	It is electricity source, it may consume electricity over-production
	 if possible (Battery with MPPT or Sell on public-grid)
	param maxPower: positive value, max power we can consume at a time.
	param minPower: negative value if we can sell or ther is battery, 0 overwise.
	"""
	def __init__(self, nameid, currentPower, maxPower, minPower, marginPower) -> None:
		# isAutoAdatative: bool, isControlable: bool, isModulable: bool, isCyclic: bool
		super().__init__(nameid, currentPower, maxPower)
		self.currentPower = currentPower
		self.marginPower = marginPower
		self.minPower = minPower

	def respectConstraints(self, power=None):
		"""
		Check min/max constraints for power
		
		return bool: true if 'power' respects constraints
		"""
		if power is None:
			power = self.currentPower.getValue()

		if power+self.marginPower.getValue()>self.maxPower.getValue():
			return False
		if power-self.marginPower.getValue()<self.minPower.getValue():
			return False
		return True

	def getMinPower(self):
		"""
		Return current minimal power
		"""
		return self.minPower.getValue()
	def getMarginPower(self):
		"""
		Return current margin power
		"""
		margin = self.marginPower.getValue()
		# logger.debug("MarginPower of Node %s is %s", self.id, margin)
		return margin

	def _getSafetyLevel(self):
		"""
		Get a int value representing how safe is the current power value

		return int:
			- 0: unsafe
			- 1: respect constraints but shouldn't on next loop
			- 2: respect constraints but could be out of constraints next loop
			- 3: Safe values
		"""
		if not self.respectConstraints():
			return 0
		_min, avg, _max = self._estimateNextPower()
		if not self.respectConstraints(avg):
			return 1
		if not (self.respectConstraints(_min) or self.respectConstraints(_max)):
			return 2
		return 3

class PublicPowerGrid(InOutNode):
	"""
	This represent Public power grid. Just one should be possible.
	"""
	def __init__(self, nameid, currentPower, maxPower, minPower, marginPower,
	             contract, networkUpdater):
		super().__init__(nameid, currentPower, maxPower, minPower, marginPower)
		self.contract = Contract.getContract(contract, networkUpdater.conf, networkUpdater)

	def __str__(self):
		return (f"PublicPowerGrid({self.currentPower}, maxPower={self.maxPower},"
			f" minPower={self.minPower}, marginPower={self.marginPower}, contract={self.contract})")

	def getContract(self):
		"""
		Return the contract. Usefull to get specificities witch can imply on strategy.
		Like offpeak-hours, prices.
		"""
		return self.contract

class SolarPanel(InOutNode):
	"""
	This represent photovoltaïc solar panels. 
	We can have many, but one can represent many solar panel.
	It depends of sensors number.
	"""
	# pylint: disable=too-many-arguments
	def __init__(self, nameid, currentPower, maxPower, *,
			moduleModel=None, inverterModel=None, tilt=45, azimuth=180,
			modulesPerString=1, stringsPerInverter=1):
		super().__init__(nameid, currentPower, maxPower, 0, 0)
		self.moduleModel = moduleModel
		self.inverterModel = inverterModel
		self.tilt = tilt
		self.azimuth = azimuth
		self.modulesPerString = modulesPerString
		self.stringsPerInverter = stringsPerInverter
	def getMaxPower(self):
		"""
		get current maximum power.
		"""
		return self.currentPower.getValue()

	def __str__(self):
		return (f"SolarPanel({self.currentPower}, {self.maxPower},"
		f" moduleModel={self.moduleModel}, inverterModel={self.inverterModel},"
		f" tilt={self.tilt}, azimuth={self.azimuth},"
		f" modulesPerString={self.modulesPerString},"
		f"stringsPerInverter={self.stringsPerInverter})")
	def __repr__(self):
		return str(self)

class Battery(InOutNode):
	"""
	This represent battery.
	"""
	# pylint: disable=too-many-arguments
	def __init__(self, nameid, capacity, currentPower, *, maxPowerIn=None,
			maxPowerOut=None, efficiencyIn:float=0.95, efficiencyOut:float=0.95,
			targetLevel:float=0.70,
			currentLevel=None, lowLevel:float=0.20, highLevel:float=0.80):
		if maxPowerIn is None:
			maxPowerIn = ConstFeeder(2300) # a standard electrical outlet
		if maxPowerOut is None:
			maxPowerOut = ConstFeeder(-1*maxPowerIn.getValue())
		super().__init__(nameid, currentPower, maxPowerIn, maxPowerOut, 0)
		self.isControlable = True
		self.isModulable = False
		self.capacity = capacity
		self.currentLevel = currentLevel
		self.lowLevel = lowLevel
		self.highLevel = highLevel
		self.targetLevel = targetLevel
		self.efficiencyIn = efficiencyIn
		self.efficiencyOut = efficiencyOut

	def getCapacity(self):
		"""
		Get battery max capacity.
		"""
		return self.capacity.getValue()

	def getLevel(self):
		"""
		Get battery level.
		"""
		return self.currentLevel.getValue()

	def __str__(self):
		return (f"Battery(capacity={self.capacity}, currentPower={self.currentPower},"
			f" maxPowerIn={self.maxPower}, maxPowerOut={self.minPower},"
			f" efficiencyIn={self.efficiencyIn}, level={self.currentLevel},"
			f" lowLevel={self.lowLevel}, highLevel={self.highLevel})")

	def __repr__(self):
		return str(self)
# class CarCharger(Switch):
# class WaterHeater(InOutNode):
