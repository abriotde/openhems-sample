""" The Simulated Annealing (recuit simulé) algorithm"""
import random
import math
import copy
import functools
from functools import lru_cache
from dataclasses import dataclass
import scipy.optimize
from openhems.modules.network.node import OutNode

def objective(x):
	previousConsumption = -1000
	previousDevicesConsumption = 0
	devicesConsumption = 0
	for i,v in enumerate(x):
		idx = int(round(v))
		# print(f"idx:{idx} for:{v} {devices[i].name}")
		l = len(devices[i].possibleValues)
		idx = idx if idx<l else l-1
		devicesConsumption += devices[i].possibleValues[idx]
	newConsumption = previousConsumption-previousDevicesConsumption+devicesConsumption
	buyOffpeakPrice = 0.15
	buyPrice = 0.3
	sellPrice = 0.1
	elseConsumption = (devicesConsumption-previousDevicesConsumption)
	if newConsumption<0:
		newPrice = newConsumption*sellPrice
	else:
		newPrice = newConsumption*buyPrice
	if elseConsumption<0:
		elsePrice = elseConsumption*sellPrice
	else:
		elsePrice = elseConsumption*buyOffpeakPrice
	ratio = newPrice-elsePrice
	print("objective(",x,") :",ratio)
	return ratio

@dataclass
class Device:
	requestedPower:float
	name:str
	possibleValues:list

devices = [
	Device(0, "pump", [0, 240]),
	Device(0, "car", [0, 500]),
	Device(0, "machine", [0, 1000])
]

def myfCB(x, y, z):
	print("take_step(",x,",",y,",",z,")")
	return False

def take_step(x):
	i = random.randint(0, len(x)-1)
	y = copy.deepcopy(x)
	current = int(round(x[i]))
	values =  range(len(devices[i].possibleValues))
	y[i] = np.random.choice([v for v in values if v != current])
	# Re-round values
	for idx,v in enumerate(y):
		roundedValue = int(round(v))
		y[idx] = roundedValue
	print("take_step(",x,",",i,") :",y)
	return y

@dataclass
class SimulatedAnnealingNode:
	"""
	This is a storage class for OpenHEMSNode parameters 
	used for SimulatedAnnealingAlgorithm
	"""
	powerMax: float
	powerValues: dict
	currentPower: float
	requestedPower: float
	name: str
	state: bool
	isUsable: bool
	isWaiting: bool
	canChangePower: bool

@dataclass
class SimulatedAnnealingAlgorithmParams:
	"""
	This is a storage class for OpenHEMSNode parameters 
	used for SimulatedAnnealingAlgorithm
	"""
	initialTemperature:float
	minTemperature:float
	coolingFactor:float
	maxNumberOfIteration:int

class SimulatedAnnealingAlgorithm:
	"""
	The class which implements the Simulated Annealing algorithm
	TODO: Instead use:
	https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.basinhopping.html
		Scipy recommends basinhopping and is more optimized/performant and can be switched easily,
		which allows customization for users.
	It's inspired by https://github.com/jmcollin78/solar_optimizer.git
	"""

	@dataclass
	class Solution:
		"""
		Used to compute solution of Simulated Annealing Algorithm
		"""
		solution:list
		target:list

		def __repr__(self):
			nodes = [(node.name+"="+str(node.requestedPower)) for node in self.solution if node.isUsable]
			return "Solution(solution=%s, target=%s)" % (nodes, self.target)

	def __init__(self, initialTemp:float=1000, minTemp:float=0.1, coolingFactor:float=0.95,
		maxIterationNumber:int=1000,logger=None):
		self.logger = logger
		"""Initialize the algorithm with values"""
		self.algoParams = SimulatedAnnealingAlgorithmParams(
			initialTemp, minTemp, coolingFactor, maxIterationNumber
		)
		self._totalPowerOfInitialEquipments: float = 0
		self.buyCost: float = 15  # in cents
		self.sellCost: float = 10  # in cents
		self.sellTax: float = 10  # in percent
		self._netConsumption: float = 0
		self.solarProduction: float = 0
		self._equipments: list[SimulatedAnnealingNode] = []
		self.logger.info(
			"Initializing the SimulatedAnnealingAlgorithm with "
			"initialTemp=%.2f minTemp=%.2f _coolingFactor=%.2f max_iterations_number=%d",
			self.algoParams.initialTemperature, self.algoParams.minTemperature,
			self.algoParams.coolingFactor, self.algoParams.maxNumberOfIteration,
		)

	def evalTarget1(solution, params):
		print("evalTarget1(",solution,", ", params,")")
		return params.evalTarget(solution)


	def coreSimulatedAnnealing1(self):
		"""
		Core algorithm of simulated annealing
		"""
		# Generate an initial solution
		
		solution = scipy.optimize.basinhopping(
			objective,
			[d.requestedPower for d in devices],
			niter=100,
			T=1.0,       # Temperature parameter
			stepsize=1, # Initial step size (not used in take_step, but required)
			minimizer_kwargs={"method": "Powell", "options": {"maxiter": 0}},  # Skip local minimization
			take_step=take_step,
			stepwise_factor=0.99999
			# accept_test=None,
			# callback=myfCB,
			# interval=50,
			# disp=False,
			# niter_success=None,
			# rng=None,
			# target_accept_rate=0.5,
		)
		print("Solution:", solution)
		return solution


	def simulatedAnnealing(self, devices:list[OutNode], powerConsumption:float,
			solarPowerProduction:float, sellCost:float, buyCost:float, sellTaxPercent:float,
			batterySoc: float):
		"""The entrypoint of the algorithm:
		You should give:
			- devices: a list of OutNode devices
			- powerConsumption: the current power consumption.
			  Can be negeative if power is given back to grid.
			- solarPowerProduction: the solar production power
			- sellCost: the sell cost of energy
			- buyCost: the buy cost of energy
			- sellTaxPercent: a sell taxe applied to sell energy (a percentage)

			In return you will have:
			- bestSolution: a list of object in which name, powerMax and state are set,
			- bestObjective: the measure of the objective for that solution,
			- totalPowerConsumption: the total of power consumption for 
			  all _equipments which should be activated (state=True)
		"""
		del batterySoc
		if ( len(devices)==0 or
				any(x is None for x in [
					powerConsumption, solarPowerProduction, sellCost, buyCost, sellTaxPercent
				]) ):
			self.logger.warning(
				"Not all informations are available for Simulated"
				"Annealing algorithm to work. Calculation is abandoned"
			)
			return [], -1, -1
		self.logger.debug(
			"Calling simulatedAnnealing with powerConsumption=%.2f, solarPowerProduction=%.2f"
			"sellCost=%.2f, buyCost=%.2f, tax=%.2f%% devices=%s",
			powerConsumption, solarPowerProduction, sellCost, buyCost, sellTaxPercent, devices,
		)
		self.buyCost = buyCost
		self.sellCost = sellCost
		self.sellTax = sellTaxPercent
		self._netConsumption = powerConsumption
		self.solarProduction = solarPowerProduction
		self._equipments = []
		for device in devices:
			powerValues = device.getControlledPowerValues() if device.isControlledPower()\
				else {0: 0, 1: device.getMaxPower()}
			self._equipments.append(
				SimulatedAnnealingNode(
					powerMax=device.getMaxPower(),
					powerValues=powerValues,
					currentPower=device.getCurrentPower(),
					requestedPower=device.getCurrentPower(),
					name=device.id,
					state=device.isOn(),
					isUsable=device.isActivate(),
					isWaiting=False,
					canChangePower=True
				)
			)
		self.logger.debug("enabled _equipments are: %s", self._equipments)
		best = self.coreSimulatedAnnealing()
		self.logger.debug("Best solution: %s", best)
		return (
			best.solution,
			best.target,
			SimulatedAnnealingAlgorithm.devicesConsumption(best.solution),
		)

	def coreSimulatedAnnealing(self):
		"""
		Core algorithm of simulated annealing
		"""
		# Generate an initial solution
		current = SimulatedAnnealingAlgorithm.Solution(None,None)
		neighbor = SimulatedAnnealingAlgorithm.Solution(None,None)
		current.solution = self.generateInitialSolution(self._equipments)
		best = SimulatedAnnealingAlgorithm.Solution(current.solution, self.evalTarget(current.solution))
		temperature = self.algoParams.initialTemperature
		# self.logger.debug("SimulatedAnnealingAlgorithm.run(%s)", self.algoParams)
		for _ in range(self.algoParams.maxNumberOfIteration):
			# Generate a neighbor
			current.target = self.evalTarget(current.solution)
			# self.logger.debug("Current : %s", current)

			# Calculate objectives for the current solution and the neighbor
			neighbor.solution = self._equipmentswap(current.solution)
			neighbor.target = self.evalTarget(neighbor.solution)
			# self.logger.debug("Neighbor : %s", neighbor)

			# Accept the neighbor if its objective is better
			# or if the total consumption does not exceed solar production
			if neighbor.target<current.target:
				self.logger.debug("---> Keeping the neighbor objective : %s", neighbor)
				current.solution = neighbor.solution
				goal = self.evalTarget(best.solution)
				if neighbor.target<goal:
					self.logger.debug("---> This is the best so far")
					best = neighbor
			else:
				# Accept the neighbor with a certain probability
				probability = math.exp(
					(current.target - neighbor.target) / temperature
				)
				if (threshold := random.random()) < probability:
					current.solution = neighbor.solution
					# self.logger.debug(
					# 	"---> Keeping the neighbor objective because "
					# 	"threshold (%.2f) is less than probability (%.2f)",
					# 	threshold, probability,
					# )
				# else: self.logger.debug("--> Not accepting")

			# Reduce the temperature
			temperature *= self.algoParams.coolingFactor
			# self.logger.debug(" !! Temperature %.2f", temperature)
			if temperature < self.algoParams.minTemperature:
				break
		return best

	def evalTarget(self, solution) -> float:
		"""
		Calculate the objective: minimize the surplus of solar production
		discharges = 0 if netConsumption >= 0 else -netConsumption
		solarConsumption = min(solarProduction, solarProduction - discharges)
		totalConsumption = netConsumption + solarConsumption
		"""
		totalEquipmentPower = SimulatedAnnealingAlgorithm.devicesConsumption(solution)
		return self.evalTargetCB(totalEquipmentPower)

	@functools.cache
	def evalTargetCB(self, totalEquipmentPower):
		totalEquipmentPowerDiff = (totalEquipmentPower - self._totalPowerOfInitialEquipments)

		newNetConsumption = self._netConsumption + totalEquipmentPowerDiff
		if newNetConsumption < 0:
			newImport = 0
			newDischarges = -newNetConsumption
		else:
			newImport = newNetConsumption
			newDischarges = 0
		newSolarConsumption = min(
			self.solarProduction, self.solarProduction - newDischarges
		)
		newTotalConsumption = (
			newNetConsumption + newDischarges
		) + newSolarConsumption
		# self.logger.debug(
		# 	"Objective: this solution adds %.3fW to the initial consumption."
		# 	"New net consumption=%.3fW. New discharges=%.3fW. New total consumption=%.3fW",
		# 	totalEquipmentPowerDiff, newNetConsumption, newDischarges, newTotalConsumption,
		# )

		forcedSellCost = self.sellCost * (1.0 - self.sellTax / 100.0)
		if self.buyCost + forcedSellCost == 0:
			self.logger.warning(
				"Buy cost and forced sell cost are <= 0. "
				"Objective is set to 0.0"
			)
			importCoefficients = 0.0
			dischargeCoefficients = 0.0
		else:
			importCoefficients = (self.buyCost) / (self.buyCost + forcedSellCost)
			dischargeCoefficients = (forcedSellCost) / (self.buyCost + forcedSellCost)
		return importCoefficients * newImport + dischargeCoefficients * newDischarges

	def generateInitialSolution(self, solution):
		"""
		Generate the initial solution (which is the solution given in argument) 
		and calculate the total initial power
		"""
		self._totalPowerOfInitialEquipments = SimulatedAnnealingAlgorithm.devicesConsumption(solution)
		return copy.deepcopy(solution)

	@staticmethod
	def devicesConsumption(solution):
		"""
		The total power consumption for all active equipment
		"""
		return sum(equipment.requestedPower
			for equipment in solution if equipment.state)

	def evalNewPower(self, equipment: SimulatedAnnealingNode):
		"""
		Calculate a new power
		"""
		choices = []
		powerMinToUse = equipment.powerValues[0]
		if equipment.currentPower > powerMinToUse:
			choices.append(-1)
		if equipment.currentPower < equipment.powerMax:
			choices.append(1)

		if len(choices) <= 0:
			# No changes
			return equipment.currentPower
		# Find the index of closest power possible value
		currentPowerIndex, currentPowerValue = min(
			equipment.powerValues.items(),
			key=lambda x: abs(equipment.currentPower - x[1])
		)
		requestedPowerIdx = random.choice(choices) + currentPowerIndex
		requestedPowerIdx = max(requestedPowerIdx, 0)
		if len(equipment.powerValues) <= requestedPowerIdx:
			requestedPowerIdx = len(equipment.powerValues) - 1
		requestedPower = equipment.powerValues.get(requestedPowerIdx)
		# self.logger.debug("Change power to %d, currentPower=%d", requestedPower, currentPowerValue)
		return requestedPower

	def _equipmentswap(self, solution):
		"""Swap the state of a random equipment"""
		neighbor = copy.deepcopy(solution)

		usable = [eqt for eqt in neighbor if eqt.isUsable]

		if len(usable) <= 0:
			return neighbor

		equipment = random.choice(usable)

		state = equipment.state
		canChangePower = equipment.canChangePower
		isWaiting = equipment.isWaiting

		# Current power is the last requestedPower
		# currentPower = equipment.requestedPower
		powerMax = equipment.powerMax
		if canChangePower:
			powerMin = equipment.powerValues[0]
		else:
			# If power is not manageable, min = max
			powerMin = powerMax

		if (not canChangePower and isWaiting) or (
			not state and canChangePower and isWaiting
		):
			self.logger.debug("not canChangePower and isWaiting -> do nothing")
			return neighbor

		if state and canChangePower and isWaiting:
			# Calculate a new power but do not switch off (because waiting)
			requestedPower = self.evalNewPower(equipment)
			assert (
				requestedPower > 0
			), "requestedPower should be > 0 because isWaiting is True"

		elif state and canChangePower and not isWaiting:
			# Change power and accept switching off
			requestedPower = self.evalNewPower(equipment)
			if requestedPower <= powerMin:
				# Deactivate the equipment
				equipment.state = False
				requestedPower = 0

		elif not state and not isWaiting:
			# Turn on
			equipment.state = not state
			requestedPower = powerMin

		elif state and not isWaiting:
			# Turn off
			equipment.state = not state
			requestedPower = 0

		elif "requestedPower" not in locals():
			self.logger.error("We should not be here. equipment=%s", equipment)
			assert False, "Requested power was not calculated. This is not normal"

		equipment.requestedPower = requestedPower

		# self.logger.debug("      -- Swapping %s max power of %.2f. It changes to %s",
		# 	equipment.name, equipment.requestedPower, equipment.state,)
		return neighbor
