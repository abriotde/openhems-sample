""" The Simulated Annealing (recuit simulé) algorithm"""
import logging
import random
import math
import copy
import scipy.optimize
from dataclasses import dataclass
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


class SimulatedAnnealingAlgorithm:
	"""
	The class which implements the Simulated Annealing algorithm
	TODO: Instead use:
	https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.basinhopping.html
		Scipy recommends basinhopping and is more optimized/performant and can be switched easily,
		which allows customization for users.
	It's inspired by https://github.com/jmcollin78/solar_optimizer.git
	"""

	temperatureInitial: float = 1000
	temperatureMinimal: float = 0.1
	coolingFactor: float = 0.95
	iterationCount: float = 1000
	equipments: list[OutNode]
	totalPowerOfInitialEquipments: float
	buyCost: float = 15  # in cents
	sellCost: float = 10  # in cents
	sellTax: float = 10  # in percent
	notConsumption: float
	solarProduction: float

	def __init__(
		self,
		initialTemp: float,
		minTemp: float,
		coolingFactor: float,
		maxIterationNumber: int,
		logger=None
	):
		self.logger = logger
		"""Initialize the algorithm with values"""
		self.temperatureInitial = initialTemp
		self.temperatureMinimal = minTemp
		self.coolingFactor = coolingFactor
		self.iterationCount = maxIterationNumber
		self.logger.info(
			"Initializing the SimulatedAnnealingAlgorithm with "
			"initialTemp=%.2f minTemp=%.2f coolingFactor=%.2f max_iterations_number=%d",
			self.temperatureInitial,
			self.temperatureMinimal,
			self.coolingFactor,
			self.iterationCount,
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
		optimizeResult = scipy.optimize.basinhopping(
			self.evalTarget,
			self.temperatureInitial,
			niter=self.iterationCount,
			T=self.coolingFactor, #
			stepsize=0.5,
			minimizer_kwargs=None, # {"method": "BFGS"}, {"method":"L-BFGS-B", "jac":True}
			take_step=None,
			accept_test=None,
			callback=None,
			interval=50,
			disp=False,
			niter_success=None,
			rng=None,
			target_accept_rate=0.5,
			stepwise_factor=0.9
		)

	def simulatedAnnealing(
		self,
		devices: list[OutNode],
		powerConsumption: float,
		solarPowerProduction: float,
		sellCost: float,
		buyCost: float,
		sellTaxPercent: float,
		batterySoc: float
	):
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
			  all equipments which should be activated (state=True)
		"""
		if (
			len(devices) <= 0  # pylint: disable=too-many-boolean-expressions
			or powerConsumption is None
			or solarPowerProduction is None
			or sellCost is None
			or buyCost is None
			or sellTaxPercent is None
		):
			self.logger.info(
				"Not all informations are available for Simulated Annealing algorithm to work. Calculation is abandoned"
			)
			return [], -1, -1

		self.logger.debug(
			"Calling simulatedAnnealing with powerConsumption=%.2f, solarPowerProduction=%.2f"
			"sellCost=%.2f, buyCost=%.2f, tax=%.2f%% devices=%s",
			powerConsumption,
			solarPowerProduction,
			sellCost,
			buyCost,
			sellTaxPercent,
			devices,
		)
		self.buyCost = buyCost
		self.sellCost = sellCost
		self.sellTax = sellTaxPercent
		self.notConsumption = powerConsumption
		self.solarProduction = solarPowerProduction

		self.equipments = []
		for device in devices:
			self.equipments.append(
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
		self.logger.debug("enabled equipments are: %s", self.equipments)

		# Generate an initial solution
		currentSolution = self.generateInitialSolution(self.equipments)
		bestSolution = currentSolution
		bestTarget = self.evalTarget(currentSolution)
		temperature = self.temperatureInitial

		for _ in range(self.iterationCount):
			# Generate a neighbor
			currentTarget = self.evalTarget(currentSolution)
			self.logger.debug("Current objective: %.2f", currentTarget)

			neighbor = self.equipmentSwap(currentSolution)

			# Calculate objectives for the current solution and the neighbor
			neighborTarget = self.evalTarget(neighbor)
			self.logger.debug("Neighbor objective: %.2f", neighborTarget)

			# Accept the neighbor if its objective is better or if the total consumption does not exceed solar production
			if neighborTarget < currentTarget:
				self.logger.debug("---> Keeping the neighbor objective")
				currentSolution = neighbor
				if neighborTarget < self.evalTarget(bestSolution):
					self.logger.debug("---> This is the best so far")
					bestSolution = neighbor
					bestTarget = neighborTarget
			else:
				# Accept the neighbor with a certain probability
				probability = math.exp(
					(currentTarget - neighborTarget) / temperature
				)
				if (threshold := random.random()) < probability:
					currentSolution = neighbor
					self.logger.debug(
							"---> Keeping the neighbor objective because threshold (%.2f) is less than probability (%.2f)",
							threshold,
							probability,
						)
				else:
					self.logger.debug("--> Not accepting")

			# Reduce the temperature
			temperature *= self.coolingFactor
			self.logger.debug(" !! Temperature %.2f", temperature)
			if temperature < self.temperatureMinimal:
				break

		return (
			bestSolution,
			bestTarget,
			SimulatedAnnealingAlgorithm.devicesConsumption(bestSolution),
		)

	def evalTarget(self, solution) -> float:
		"""
		Calculate the objective: minimize the surplus of solar production
		discharges = 0 if netConsumption >= 0 else -netConsumption
		solarConsumption = min(solarProduction, solarProduction - discharges)
		totalConsumption = netConsumption + solarConsumption
		"""
		totalEquipmentPower = SimulatedAnnealingAlgorithm.devicesConsumption(solution)
		totalEquipmentPowerDiff = (
			totalEquipmentPower - self.totalPowerOfInitialEquipments
		)

		newNetConsumption = self.notConsumption + totalEquipmentPowerDiff
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
		self.totalPowerOfInitialEquipments = SimulatedAnnealingAlgorithm.devicesConsumption(solution)
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
		if requestedPowerIdx < 0:
			requestedPowerIdx = 0
		if len(equipment.powerValues) <= requestedPowerIdx:
			requestedPowerIdx = len(equipment.powerValues) - 1
		requestedPower = equipment.powerValues.get(requestedPowerIdx)
		self.logger.debug("Change power to %d, currentPower=%d", requestedPower, currentPowerValue)
		return requestedPower

	def equipmentSwap(self, solution):
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
		currentPower = equipment.requestedPower
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
