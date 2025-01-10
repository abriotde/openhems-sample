"""
Represent device of home network
"""

import logging
from collections import deque
from typing import Final
from openhems.modules.web import OpenHEMSSchedule
from openhems.modules.contract import Contract
from .feeder import Feeder

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

	def __init__(self, nameId, currentPower, maxPower, isOnFeeder=None):
		self.id = ""
		self.setId(nameId)
		self.params = ""
		self.network = None
		self._isSwitchable = False
		self._isOn: Feeder = None
		self.currentPower: Feeder = 0
		self.maxPower: Feeder = 2000
		self.currentPower = currentPower
		self.maxPower = maxPower
		if isOnFeeder is not None:
			self._isOn = isOnFeeder
			self._isSwitchable = True
		else:
			self._isSwitchable = False
		self.previousPower = deque()

	def setCurrentPower(self, currentPower):
		"""
		Get current power.
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
		if self._isSwitchable and not self.isOn() and currentPower!=0:
			logger.warning("'%s' is Off but current power=%d", self.id, currentPower)
		logger.info("OpenHEMSNode.getCurrentPower() = %d", currentPower)
		return currentPower

	def getMaxPower(self):
		"""
		Get max power 
		"""
		return self.maxPower.getValue()

	def estimateNextPower(self):
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

	def isSwitchable(self):
		"""
			Return true if this OpenHEMSNode can be switch on/off.
		"""
		return self._isSwitchable

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
		if self._isSwitchable:
			return self.network.networkUpdater.switchOn(connect, self)
		logger.warning("Try to switchOn/Off a not switchable device : %s", self.id)
		return connect # Consider node is always on network

class OutNode(OpenHEMSNode):
	"""
	Electricity consumer (like washing-machine, water-heater).
	"""
	def __init__(self, nameId, strategyId, currentPower, maxPower, isOnFeeder=None):
		super().__init__(nameId, currentPower, maxPower, isOnFeeder)
		self.name = nameId
		self.schedule = OpenHEMSSchedule(self.id, nameId)
		self.strategyId = strategyId

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
		return (f"OutNode(name={self.name}, strategy={self.strategyId},"
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
		return self.marginPower.getValue()

	def getSafetyLevel(self):
		"""
		Get a int value representing how safe is the current power value

		return int:
			- 0: unsafe
			- 1: respect constraints but shouldn't on nex loop
			- 2: respect constraints but could be out of constraints next loop
			- 3: Safe values
		"""
		if not self.respectConstraints():
			return 0
		_min, avg, _max = self.estimateNextPower()
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
			maxPowerOut=None, marginPower=None,
			currentLevel=None, lowLevel=None, hightLevel=None):
		if maxPowerIn is None:
			maxPowerIn = 2000
		if maxPowerOut is None:
			maxPowerOut = -1 * maxPowerIn
		if lowLevel is None:
			lowLevel = 0.2*capacity
		if hightLevel is None:
			hightLevel = 0.8*capacity
		if marginPower is None:
			marginPower = capacity*0.1
		super().__init__(nameid, currentPower, maxPowerIn, maxPowerOut, marginPower)
		self.isControlable = True
		self.isModulable = False
		self.capacity = capacity
		self.currentLevel = currentLevel
		self.lowLevel = lowLevel
		self.hightLevel = hightLevel

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
			f" marginPower={self.marginPower}, level={self.currentLevel},"
			f" lowLevel={self.lowLevel}, hightLevel={self.hightLevel})")

	def __repr__(self):
		return str(self)
# class CarCharger(Switch):
# class WaterHeater(InOutNode):
