""" The Simulated Annealing (recuit simulé) algorithm"""
import random
import math
import copy
from dataclasses import dataclass
import scipy.optimize
from openhems.modules.network.node import OutNode

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
		self._notConsumption: float = 0
		self.solarProduction: float = 0
		self._equipments: list[SimulatedAnnealingNode] = []
		self.logger.info(
			"Initializing the SimulatedAnnealingAlgorithm with "
			"initialTemp=%.2f minTemp=%.2f _coolingFactor=%.2f max_iterations_number=%d",
			self.algoParams.initialTemperature, self.algoParams.minTemperature,
			self.algoParams.coolingFactor, self.algoParams.maxNumberOfIteration,
		)

	def basinhopping(
		self,
		devices: list[OutNode],
		powerConsumption: float,
		solarPowerProduction: float,
		sellCost: float,
		buyCost: float,
		sellTaxPercent: float,
		batterySoc: float
	):
		"""
		Seam impossible because not all devices are variable consumption devices.
		"""
		del devices, powerConsumption, solarPowerProduction, batterySoc
		del sellCost, buyCost, sellTaxPercent
		scipy.optimize.basinhopping(
			self.evalTarget,
			self.algoParams.initialTemperature,
			niter=self.algoParams.maxNumberOfIteration,
			T=self.algoParams.coolingFactor, #
			stepsize=0.5,
			minimizer_kwargs=None, # {"method": "BFGS"}, {"method":"L-BFGS-B", "jac":True}
			take_step=None,
			accept_test=None,
			callback=None,
			interval=50,
			disp=False,
			niter_success=None,
			# rng=None,
			target_accept_rate=0.5,
			stepwise_factor=0.9
		)


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
		self._notConsumption = powerConsumption
		self.solarProduction = solarPowerProduction
		self._equipments = []
		for device in devices:
			self._equipments.append(
				SimulatedAnnealingNode(
					powerMax=device.getMaxPower(),
					powerValues=device.getControlledPowerValues(),
					currentPower=device.getCurrentPower(),
					requestedPower=device.getControlledPower(),
					name=device.id,
					state=device.isOn(),
					isUsable=device.isActivate(),
					isWaiting=False,
					canChangePower=device.isControlledPower()
				)
			)
		self.logger.debug("enabled _equipments are: %s", self._equipments)
		best = self.coreSimulatedAnnealing()
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
		current = SimulatedAnnealingAlgorithm.Solution(0,0)
		neighbor = SimulatedAnnealingAlgorithm.Solution(0,0)
		current.solution = self.generateInitialSolution(self._equipments)
		best = SimulatedAnnealingAlgorithm.Solution(current.solution, self.evalTarget(current.solution))
		temperature = self.algoParams.initialTemperature

		for _ in range(self.algoParams.maxNumberOfIteration):
			# Generate a neighbor
			current.target = self.evalTarget(current.solution)
			self.logger.debug("Current objective: %.2f", current.target)

			# Calculate objectives for the current solution and the neighbor
			neighbor.solution = self._equipmentswap(current.solution)
			neighbor.target = self.evalTarget(neighbor.solution)
			self.logger.debug("Neighbor objective: %.2f", neighbor.target)

			# Accept the neighbor if its objective is better
			# or if the total consumption does not exceed solar production
			if neighbor.target<current.target:
				self.logger.debug("---> Keeping the neighbor objective")
				current.solution = neighbor.solution
				if neighbor.target<self.evalTarget(best.solution):
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
							threshold,
							probability,
						)
				else:
					self.logger.debug("--> Not accepting")

			# Reduce the temperature
			temperature *= self.algoParams.coolingFactor
			self.logger.debug(" !! Temperature %.2f", temperature)
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
		totalEquipmentPowerDiff = (
			totalEquipmentPower - self._totalPowerOfInitialEquipments
		)

		newNetConsumption = self._notConsumption + totalEquipmentPowerDiff
		newDischarges = 0 if newNetConsumption >= 0 else -newNetConsumption
		newImport = 0 if newNetConsumption < 0 else newNetConsumption
		newSolarConsumption = min(
			self.solarProduction, self.solarProduction - newDischarges
		)
		newTotalConsumption = (
			newNetConsumption + newDischarges
		) + newSolarConsumption
		self.logger.debug(
				"Objective: this solution adds %.3fW to the initial consumption."
				"New net consumption=%.3fW. New discharges=%.3fW. New total consumption=%.3fW",
				totalEquipmentPowerDiff,
				newNetConsumption,
				newDischarges,
				newTotalConsumption,
			)

		forcedSellCost = self.sellCost * (1.0 - self.sellTax / 100.0)
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
		return sum(
			equipment.requestedPower
			for equipment in solution
			if equipment.state
		)

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

		self.logger.debug(
				"      -- Swapping %s max power of %.2f. It changes to %s",
				equipment.name,
				equipment.requestedPower,
				equipment.state,
			)
		return neighbor
