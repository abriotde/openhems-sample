""" The Simulated Annealing (recuit simulé) algorithm"""
import random
import math
import copy
import functools
from dataclasses import dataclass
from enum import Enum
import scipy.optimize
import numpy as np
from openhems.modules.network import OutNode


# Study of solutions:
# - Genetic Algorithm
# - Simulated annealing
#   - From solar-optimizer
#   - Using scipy.optimize.basinhopping
#   - From custom (coreSimulatedAnnealing2)
#   Problem: Results to random, difficulties to use standard due to discrete values.
# - PuLP (for linear integer programming):
# - DEAP (flexible evolutionary algorithms):
# - Optuna (hyperparameter optimization, supports discrete spaces):

# [PV-Excess-Control]
#   (https://github.com/InventoCasa/ha-advanced-blueprints/tree/main/PV_Excess_Control)
# [Solar-Optimizer](https://github.com/jmcollin78/solar_optimizer.git)

class Algorithme(Enum):
	"""
	List of all implemented (or study) algorithmes
	"""
	SIMULATED_ANNEAALING_SOLAROPTIMIZER = 1
	SIMULATED_ANNEAALING_CUSTOM = 2
	BASIN_HOPPING_SCIPY = 3 # Close to SIMULATED_ANNEAALING, can be reduce to it.
	GENETIC = 4

class OptimizationAlgorithm:
	"""
	The class which implements the Simulated Annealing algorithm
	TODO: Instead use:
	https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.basinhopping.html
		Scipy recommends basinhopping and is more optimized/performant and can be switched easily,
		which allows customization for users.
	It's inspired by https://github.com/jmcollin78/solar_optimizer.git
	"""
	GENETIC_MODULO = 64

	@dataclass
	class Solution:
		"""
		Used to compute solution of Simulated Annealing Algorithm
		"""
		solution:list
		target:float

		def __repr__(self):
			nodes = [(node.name+"="+str(node.requestedPower)) for node in self.solution if node.isUsable]
			return f"Solution(solution={nodes}, target={self.target})"

	@dataclass
	class SimulatedAnnealingAlgorithmParams:
		"""
		This is a storage class for OpenHEMSNode parameters 
		used for OptimizationAlgorithm
		"""
		initialTemperature:float
		minTemperature:float
		coolingFactor:float
		maxNumberOfIteration:int

	@dataclass
	class Node:
		"""
		This is a storage class for OpenHEMSNode parameters 
		used for OptimizationAlgorithm
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
	class Prices:
		"""
		Prices used for algorythmes
		"""
		buy:float
		offpeak:float
		sell:float
		sellTax:float


	def __init__(self, initialTemp:float=1000, minTemp:float=0.1, coolingFactor:float=0.95,
		maxIterationNumber:int=1000,logger=None, algo=Algorithme.GENETIC):
		self.logger = logger
		"""Initialize the algorithm with values"""
		self.algoParams = OptimizationAlgorithm.SimulatedAnnealingAlgorithmParams(
			initialTemp, minTemp, coolingFactor, maxIterationNumber
		)
		self._totalPowerOfInitialEquipments: float = 0
		self._netConsumption: float = 0
		self.solarProduction: float = 0
		self._equipments: list[OptimizationAlgorithm.Node] = []
		self.logger.info(
			"Initializing the SimulatedAnnealingAlgorithm with "
			"initialTemp=%.2f minTemp=%.2f _coolingFactor=%.2f max_iterations_number=%d",
			self.algoParams.initialTemperature, self.algoParams.minTemperature,
			self.algoParams.coolingFactor, self.algoParams.maxNumberOfIteration,
		)
		self.algo = algo
		self.prices = None
		# pylint: disable=import-error, import-outside-toplevel
		from sko.GA import GA # pip install scikit-opt
		self.skoGa = GA

	def takeStep(self, x):
		"""
		Function to determine neightboor for scipy.optimize.basinhopping
		"""
		i = random.randint(0, len(x)-1)
		y = copy.deepcopy(x)
		current = int(round(x[i]))
		values =  range(len(self._equipments[i].powerValues))
		y[i] = np.random.choice([v for v in values if v != current])
		# Re-round values
		for idx,v in enumerate(y):
			roundedValue = int(round(v))
			y[idx] = roundedValue
		# print("take_step(",x,",",i,") :",y)
		return y

	def objective(self, x):
		"""
		Objective function to optimize for scipy.optimize.basinhopping
		"""
		devicesConsumption = 0
		for i,v in enumerate(x):
			idx = int(round(v))
			values = self._equipments[i].powerValues
			# print(f"idx:{idx} for:{v} {values[i].name}")
			l = len(values)
			idx = idx if idx<l else l-1
			devicesConsumption += values[idx]
		newConsumption = self._netConsumption-self._totalPowerOfInitialEquipments+devicesConsumption
		elseConsumption = devicesConsumption-self._totalPowerOfInitialEquipments
		if newConsumption<0:
			newPrice = newConsumption*self.prices.sell
		else:
			newPrice = newConsumption*self.prices.buy
		if elseConsumption<0:
			elsePrice = elseConsumption*self.prices.sell
		else:
			elsePrice = elseConsumption*self.prices.offpeak
		ratio = newPrice-elsePrice
		# print("objective(",x,") :",ratio)
		return ratio

	def bassinhopping(self):
		"""
		Core algorithm of simulated annealing using scipy.optimize.basinhopping
		"""
		# Generate an initial solution
		solution = scipy.optimize.basinhopping(
			self.objective,
			[d.requestedPower for d in self._equipments],
			niter=100,
			T=1.0,       # Temperature parameter
			stepsize=1, # Initial step size (not used in take_step, but required)
			minimizer_kwargs={"method": "Powell", "options": {"maxiter": 0}},  # Skip local minimization
			take_step=self.takeStep,
			stepwise_factor=0.99999
			# accept_test=None,
			# callback=myfCB,
			# interval=50,
			# disp=False,
			# niter_success=None,
			# rng=None,
			# target_accept_rate=0.5,
		)
		self.logger.debug("Solution: %s", solution)
		return solution

	def coreSimulatedAnnealing2(self):
		"""
		Custum implementation based on IA
		"""
		initialState = [v.currentPower for v in self._equipments]
		current = OptimizationAlgorithm.Solution(initialState, self.objective(initialState))
		temp = self.algoParams.initialTemperature
		for _ in range(self.algoParams.maxNumberOfIteration):
			# Generate neighbor by flipping one random variable
			neighbor = OptimizationAlgorithm.Solution(current.solution.copy(), 0)
			# Choose a random value in the vector
			idx = int(np.random.randint(0, len(neighbor.solution)))
			currentVal = neighbor.solution[idx]
			allowedValues = self._equipments[idx].powerValues
			neighbor.solution[idx] = np.random.choice([v for v in allowedValues if v != currentVal])
			neighbor.target = self.objective(neighbor.solution)
			costDiff = neighbor.target - current.target
			# Accept better solutions or worse with a probability
			if costDiff < 0 or np.exp(-costDiff / temp) > np.random.rand():
				current = neighbor
			# Cool down temperature
			temp *= 0.95
		return current

	def run(self, devices:list[OutNode], powerConsumption:float,
			solarPowerProduction:float, sellCost:float, buyCost:float,
			batterySoc: float, offpeakPrice:float):
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
					powerConsumption, solarPowerProduction, sellCost, buyCost, offpeakPrice
				]) ):
			self.logger.warning(
				"Not all informations are available for Simulated"
				"Annealing algorithm to work. Calculation is abandoned"
			)
			return [], -1, -1
		self.logger.debug(
			"Calling simulatedAnnealing with powerConsumption=%.2f, solarPowerProduction=%.2f"
			"sellCost=%.2f, buyCost=%.2f, offpeakCost=%.2f%% devices=%s",
			powerConsumption, solarPowerProduction, sellCost, buyCost, offpeakPrice, devices,
		)
		self.prices = OptimizationAlgorithm.Prices(buyCost, offpeakPrice, sellCost, 0.3)
		self._netConsumption = powerConsumption
		self.solarProduction = solarPowerProduction
		self._equipments = []
		for device in devices:
			powerValues = device.getControlledPowerValues() if device.isControlledPower()\
				else {0: 0, 1: device.getMaxPower()}
			self._equipments.append(
				OptimizationAlgorithm.Node(
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
		match self.algo:
			case Algorithme.SIMULATED_ANNEAALING_SOLAROPTIMIZER:
				best = self.coreSimulatedAnnealing()
			case Algorithme.SIMULATED_ANNEAALING_CUSTOM:
				best = self.coreSimulatedAnnealing2()
			case Algorithme.BASIN_HOPPING_SCIPY:
				best = self.bassinhopping()
			case Algorithme.GENETIC:
				best = self.geneticAlgorithm()
		self.logger.debug("Best solution: %s", best)
		return (
			best.solution,
			best.target,
			OptimizationAlgorithm.devicesConsumption(best.solution),
		)

	def coreSimulatedAnnealing(self):
		"""
		Core algorithm of simulated annealing
		"""
		# Generate an initial solution
		current = OptimizationAlgorithm.Solution(None,None)
		neighbor = OptimizationAlgorithm.Solution(None,None)
		current.solution = self.generateInitialSolution(self._equipments)
		best = OptimizationAlgorithm.Solution(current.solution, self.evalTarget(current.solution))
		temperature = self.algoParams.initialTemperature
		# self.logger.debug("OptimizationAlgorithm.run(%s)", self.algoParams)
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
					self.logger.debug(
						"---> Keeping the neighbor objective because "
						"threshold (%.2f) is less than probability (%.2f)",
						threshold, probability,
					)
				# else: self.logger.debug("--> Not accepting")

			# Reduce the temperature
			temperature *= self.algoParams.coolingFactor
			# self.logger.debug(" !! Temperature %.2f", temperature)
			if temperature < self.algoParams.minTemperature:
				break
		return best

	def evalTarget2(self, solution):
		"""
		Custom implementation of evalTarget()
		"""
		basedConsumption = self._netConsumption-self._totalPowerOfInitialEquipments
		devicesConsumption = OptimizationAlgorithm.devicesConsumption(solution)
		newConsumption = basedConsumption+devicesConsumption
		# Price if we use this consumption
		if newConsumption<0:
			newPrice = newConsumption*self.prices.sell
		else:
			newPrice = newConsumption*self.prices.buy
		# Price if we report consumption on night
		if basedConsumption<0:
			elsePrice = basedConsumption*self.prices.sell
		else:
			elsePrice = basedConsumption*self.prices.offpeak
		ratio = newPrice-elsePrice
		self.logger.debug("evalTarget2(%s) : %s",solution,ratio)
		return ratio

	def evalTarget(self, solution) -> float:
		"""
		Calculate the objective: minimize the surplus of solar production
		discharges = 0 if netConsumption >= 0 else -netConsumption
		solarConsumption = min(solarProduction, solarProduction - discharges)
		totalConsumption = netConsumption + solarConsumption
		"""
		totalEquipmentPower = OptimizationAlgorithm.devicesConsumption(solution)
		return self.evalTargetCB(totalEquipmentPower)

	@functools.lru_cache(maxsize=10000)
	def evalTargetCB(self, totalEquipmentPower):
		"""
		Callback of evalTarget() used for cache because 'solution' is unhashable
		"""
		totalEquipmentPowerDiff = totalEquipmentPower - self._totalPowerOfInitialEquipments
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
		self.logger.debug(
			"Objective: this solution adds %.3fW to the initial consumption."
			"New net consumption=%.3fW. New discharges=%.3fW. New total consumption=%.3fW",
			totalEquipmentPowerDiff, newNetConsumption, newDischarges, newTotalConsumption,
		)
		forcedSellCost = self.prices.sell * (1.0 - self.prices.sellTax / 100.0)
		if self.prices.buy + forcedSellCost == 0:
			self.logger.warning(
				"Buy cost and forced sell cost are <= 0. "
				"Objective is set to 0.0"
			)
			importCoefficients = 0.0
			dischargeCoefficients = 0.0
		else:
			importCoefficients = (self.prices.buy) / (self.prices.buy + forcedSellCost)
			dischargeCoefficients = (forcedSellCost) / (self.prices.buy + forcedSellCost)
		return importCoefficients * newImport + dischargeCoefficients * newDischarges

	def generateInitialSolution(self, solution):
		"""
		Generate the initial solution (which is the solution given in argument) 
		and calculate the total initial power
		"""
		self._totalPowerOfInitialEquipments = OptimizationAlgorithm.devicesConsumption(solution)
		return copy.deepcopy(solution)

	@staticmethod
	def devicesConsumption(solution):
		"""
		The total power consumption for all active equipment
		"""
		return sum(equipment.requestedPower
			for equipment in solution if equipment.state)

	def evalNewPower(self, equipment):
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
		self.logger.debug("Change power to %d, currentPower=%d", requestedPower, currentPowerValue)
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

	@functools.lru_cache(maxsize=20000)
	def geneticGetPower(self, fakeValue, index):
		"""
		Retrieve the real value from the fakeValue
		witch is a number between 0 and OptimizationAlgorithm.GENETIC_MODULO
		"""
		realValues = self._equipments[index].powerValues
		l = len(realValues)
		if l<OptimizationAlgorithm.GENETIC_MODULO:
			idx = fakeValue%l
		else:
			fact = l/OptimizationAlgorithm.GENETIC_MODULO
			idx = round(fact*fakeValue)
			if idx >= l:
				idx = l-1
		return realValues[idx]

	def evalTarget3(self, x):
		"""
		Function to optimize for geneticAlgorithm()
		"""
		devicesConsumption = 0
		for i,v in enumerate(x):
			devicesConsumption += self.geneticGetPower(v, i)
		return self.evalTarget3CB(devicesConsumption)

	@functools.lru_cache(maxsize=5000)
	def evalTarget3CB(self, devicesConsumption):
		"""
		Call-back of function to optimize for geneticAlgorithm().
		Used for cache because list parameters can't be cached.
		"""
		# Price if we use this consumption
		basedConsumption = self._netConsumption-self._totalPowerOfInitialEquipments
		newConsumption = basedConsumption+devicesConsumption
		if newConsumption<0:
			newPrice = newConsumption*self.prices.sell
		else:
			newPrice = newConsumption*self.prices.buy
		# Price if we report consumption on night
		elseConsumption = basedConsumption+self.solarProduction
		if elseConsumption<0:
			elsePrice = elseConsumption*self.prices.sell
		else:
			elsePrice = elseConsumption*self.prices.offpeak
		ratio = pow(newPrice-elsePrice, 2)
		self.logger.debug("evalTarget3(%s) : Consumption: %s;%s : prices: %s;%s : %s",
				devicesConsumption,newConsumption,elseConsumption,newPrice,elsePrice,ratio)
		return ratio

	def geneticAlgorithm(self):
		"""
		Use genetic algorythm to find the best solution
		"""
		ga = self.skoGa(
			func=self.evalTarget3,
			n_dim=len(self._equipments),
			size_pop=50,      # Population size
			max_iter=200,     # Generations
			prob_mut=0.1,     # Mutation probability
			lb=0, ub=OptimizationAlgorithm.GENETIC_MODULO, # Use modulo to adapt
			precision=1,      # Treat variables as integers (0 or 1)
		)
		bestX, bestY = ga.run()
		for i,v in enumerate(bestX):
			self._equipments[i].requestedPower = self.geneticGetPower(v, i)
		best = OptimizationAlgorithm.Solution(self._equipments, bestY)
		# Clear caches to free memory
		#  on next call class's attributes will be differents, so caches will be wrong.
		# self.logger.debug("Caches : %s; %s;",
		# 	self.evalTarget3CB.cache_info(), self.geneticGetPower.cache_info())
		self.evalTarget3CB.cache_clear()
		self.geneticGetPower.cache_clear()
		return best
