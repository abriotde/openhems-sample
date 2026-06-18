"""
Represent device of home network
"""

from openhems.modules.contract import Contract
from openhems.modules.util import DangerousStateException
from .feeder import ConstFeeder
from .node import Node

class InOutNode(Node):
	"""
	It is electricity source, it may consume electricity over-production
	 if possible (Battery with MPPT or Sell on public-grid)
	param maxPower: positive value, max power we can consume at a time.
	param minPower: negative value if we can sell or ther is battery, 0 overwise.
	"""
	def __init__(self, nameid, currentPower, *, maxPower=2300, minPower=0, marginPower=0) -> None:
		# isAutoAdatative: bool, isControlable: bool, isModulable: bool, isCyclic: bool
		super().__init__(nameid, currentPower, maxPower)
		self.marginPower = marginPower
		self.minPower = minPower

	def respectConstraints(self, power=None):
		"""
		Check min/max constraints for power
		
		return bool: true if 'power' respects constraints
		"""
		if power is None:
			power = self._currentPower.getValue()
		marginPower = self.marginPower.getValue()
		maxPower = self.getMaxPower()
		if maxPower is not None and power+marginPower>maxPower:
			self.network.logger.warning("Node %s is over maxPower (%s > %s)",
				self.id, power+marginPower, maxPower)
			return False
		minPower = self.getMinPower()
		if minPower is not None and power-marginPower<minPower:
			self.network.logger.warning("Node %s is under minPower (%s < %s)",
				self.id, power-marginPower, self.minPower.getValue())
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

	# def _getSafetyLevel(self):
	# 	"""
	# 	Get a int value representing how safe is the current power value
	#
	# 	return int:
	# 		- 0: unsafe
	# 		- 1: respect constraints but shouldn't on next loop
	# 		- 2: respect constraints but could be out of constraints next loop
	# 		- 3: Safe values
	# 	"""
	# 	if not self.respectConstraints():
	# 		return 0
	# 	# _min, avg, _max = self._estimateNextPower()
	# 	# if not self.respectConstraints(avg):
	# 	# 	return 1
	# 	# if not (self.respectConstraints(_min) or self.respectConstraints(_max)):
	# 	# 	return 2
	# 	return 3

class PublicPowerGrid(InOutNode):
	"""
	This represent Public power grid. Just one should be possible.
	"""
	def __init__(self, nameid, currentPower, maxPower, minPower, *, marginPower,
	             contract=None, networkUpdater=None):
		super().__init__(nameid, currentPower,
				   maxPower=maxPower, minPower=minPower, marginPower=marginPower)
		self.contract = Contract.getContract(contract, networkUpdater.conf, networkUpdater)

	def __str__(self):
		return (f"PublicPowerGrid({self._currentPower}, maxPower={self._maxPower},"
			f" minPower={self.minPower}, marginPower={self.marginPower}, contract={self.contract})")

	def getContract(self):
		"""
		Return the contract. Usefull to get specificities witch can imply on strategy.
		Like offpeak-hours, prices.
		"""
		return self.contract

	def updateEnergy(self, energy:float, duration:float, now=None):
		"""
		Fonction used only on Fake network to force publicpowergrid 
		to consume all over productions/consumptions.
		"""
		# TODO : check max/min power
		print("PublicPowerGrid.updateEnergy(",energy,", ",duration,")")
		del now
		power = energy/duration
		if power>self.getMaxPower():
			raise DangerousStateException(
				f"Reach PublicPowerGrid max power : {power} > {self.getMaxPower()}",
				"OVER_CONSUMPTION"
			)
		if -self.getMinPower()>power:
			# raise DangerousStateException(
			# 	f"Reach PublicPowerGrid min power : {-self.getMinPower()} > {power}",
			# 	"OVER_CONSUMPTION"
			# )
			self.logger.error(
				"Reach PublicPowerGrid min power : {%s} > {%s} ", -self.getMinPower(), power
			)
		node = self._currentPower
		if hasattr(node, '_currentPower'):
			node.setValue(power)
		return 0

class SolarPanel(InOutNode):
	"""
	This represent photovoltaïc solar panels. 
	We can have many, but one can represent many solar panel.
	It depends of sensors number.
	"""
	# pylint: disable=too-many-arguments
	def __init__(self, nameid, currentPower, maxPower, *,
			moduleModel=None, inverterModel=None, tilt=45, azimuth=180,
			modulesPerString=1, stringsPerInverter=1, marginPower=None):
		if marginPower is None:
			marginPower = ConstFeeder(0)
		super().__init__(nameid, currentPower,
				maxPower=maxPower, minPower=0, marginPower=marginPower)
		self.moduleModel = moduleModel
		self.inverterModel = inverterModel
		self.tilt = tilt
		self.azimuth = azimuth
		self.modulesPerString = modulesPerString
		self.stringsPerInverter = stringsPerInverter

	def getMaxPower(self):
		"""
		get current maximum power = current power.
		value saved in maxPower, is the theorical maxPower (usefull to know efficiency).
		But in fact even if we ask more power, solar panels can't give us more.
		"""
		return self._currentPower.getValue()

	def __str__(self):
		return (f"SolarPanel({self._currentPower}, {self._maxPower},"
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
		super().__init__(nameid, currentPower, maxPower=maxPowerIn, minPower=maxPowerOut, marginPower=0)
		self.isControlable = True
		self.isModulable = True
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
		return (f"Battery(capacity={self.capacity}, currentPower={self._currentPower},"
			f" maxPowerIn={self._maxPower}, maxPowerOut={self.minPower},"
			f" efficiencyIn={self.efficiencyIn}, level={self.currentLevel},"
			f" lowLevel={self.lowLevel}, highLevel={self.highLevel})")

	def __repr__(self):
		return str(self)

# pylint: disable=invalid-name

class FakeBattery(Battery):
	"""
	This represent a fake battery. It is usefull for test or simulation.
	"""
	# pylint: disable=too-many-arguments
	def __init__(self, nameid, capacity, currentPower, *, maxPowerIn=None,
			maxPowerOut=None, efficiencyIn:float=0.95, efficiencyOut:float=0.95,
			targetLevel:float=0.70,
			currentLevel=None, lowLevel:float=0.20, highLevel:float=0.80):
		super().__init__(nameid, capacity, currentPower,
			maxPowerIn=maxPowerIn, maxPowerOut=maxPowerOut,
			efficiencyIn=efficiencyIn, efficiencyOut=efficiencyOut,
			targetLevel=targetLevel,
			currentLevel=currentLevel, lowLevel=lowLevel, highLevel=highLevel)
		self._max_energy_stored = capacity.getValue()
		self._energy_stored = self._max_energy_stored * 0.50


	def getLevel(self):
		"""
		Get battery level.
		"""
		return self._energy_stored/self._max_energy_stored*100

	def updateEnergy(self, energy:float, duration:float, now=None):
		"""
		At each cycle, we will set how mutch power we want to store/give back.
		energy : energy we want to store (positive) or give back (negative)
		"""
		del now
		in_power = energy/duration
		overdemand = 0
		if in_power>self.getMaxPower():
			e = self.getMaxPower()*duration
			overdemand = energy - e
			energy = e
		elif in_power<self.getMinPower():
			e = self.getMinPower()*duration
			overdemand = energy - e
			energy = e
		if energy>0:
			# We store energy, we have to take care of efficiency
			loss_coef = self.efficiencyIn
		else:
			# We give back energy, we have to take care of efficiency
			loss_coef = self.efficiencyOut
		self._energy_stored += energy * loss_coef
		if self._energy_stored>self._max_energy_stored:
			overdemand += self._energy_stored - self._max_energy_stored
			self._energy_stored = self._max_energy_stored
		elif self._energy_stored<0:
			overdemand += self._energy_stored
			self._energy_stored = 0
		return overdemand



# class CarCharger(Switch):
# class WaterHeater(InOutNode):
