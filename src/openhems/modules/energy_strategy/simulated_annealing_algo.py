""" The Simulated Annealing (recuit simulé) algorithm"""
import logging
import random
import math
import copy

from openhems.modules.network.node import OutNode

class SimulatedAnnealingAlgorithm:
	"""
	The class which implemenets the Simulated Annealing algorithm
	"""

	_temperature_initiale: float = 1000
	_temperature_minimale: float = 0.1
	_coolingFactor: float = 0.95
	_nombre_iterations: float = 1000
	_equipements: list[OutNode]
	_totalPowerOfInitialEqt: float
	_buyCost: float = 15  # in cents
	_sellCost: float = 10  # in cents
	_sellTax: float = 10  # in percent
	_notConsumption: float
	_productionSolaire: float

	def __init__(
		self,
		initial_temp: float,
		min_temp: float,
		cooling_factor: float,
		max_iteration_number: int,
		logger=None
	):
		self._logger = logger
		"""Initialize the algorithm with values"""
		self._temperature_initiale = initial_temp
		self._temperature_minimale = min_temp
		self._coolingFactor = cooling_factor
		self._nombre_iterations = max_iteration_number
		self._logger.info(
			"Initializing the SimulatedAnnealingAlgorithm with initial_temp=%.2f min_temp=%.2f cooling_factor=%.2f max_iterations_number=%d",
			self._temperature_initiale,
			self._temperature_minimale,
			self._coolingFactor,
			self._nombre_iterations,
		)

	def simulatedAnnealing(
		self,
		devices: list[OutNode],
		powerConsumption: float,
		solar_power_production: float,
		sellCost: float,
		buyCost: float,
		sell_tax_percent: float,
		battery_soc: float
	):
		"""The entrypoint of the algorithm:
		You should give:
			- devices: a list of OutNode devices
			- powerConsumption: the current power consumption. Can be negeative if power is given back to grid.
			- solar_power_production: the solar production power
			- sellCost: the sell cost of energy
			- buyCost: the buy cost of energy
			- sell_tax_percent: a sell taxe applied to sell energy (a percentage)

			In return you will have:
			- best_solution: a list of object in whitch name, powerMax and state are set,
			- best_objectif: the measure of the objective for that solution,
			- total_powerConsumption: the total of power consumption for all equipments which should be activated (state=True)
		"""
		if (
			len(devices) <= 0  # pylint: disable=too-many-boolean-expressions
			or powerConsumption is None
			or solar_power_production is None
			or sellCost is None
			or buyCost is None
			or sell_tax_percent is None
		):
			self._logger.info(
				"Not all informations are available for Simulated Annealign algorithm to work. Calculation is abandoned"
			)
			return [], -1, -1

		self._logger.debug(
			"Calling recuit_simule with powerConsumption=%.2f, solar_power_production=%.2f sellCost=%.2f, buyCost=%.2f, tax=%.2f%% devices=%s",
			powerConsumption,
			solar_power_production,
			sellCost,
			buyCost,
			sell_tax_percent,
			devices,
		)
		self._buyCost = buyCost
		self._sellCost = sellCost
		self._sellTax = sell_tax_percent
		self._notConsumption = powerConsumption
		self._productionSolaire = solar_power_production

		self._equipements = []
		for device in devices:
			self._equipements.append(
				{
					"powerMax": device.getMaxPower(),
					"powerMin": device.getMinPower(),
					"powerStep": 1,
					"current_power": device.getCurrentPower(),
					# Initial Requested power is the current power if usable
					"requested_power": device.getCurrentPower(),
					"name": device.id,
					"state": device.isOn(),
					"is_usable": True,
					"isWaiting": False,
					"canChangePower": device.isControlledPower()
				}
			)
		self._logger.debug("enabled _equipements are: %s", self._equipements)

		# Générer une solution initiale
		currentSolution = self.genererateInitialeSolution(self._equipements)
		bestSolution = currentSolution
		bestTarget = self.evalTarget(currentSolution)
		temperature = self._temperature_initiale

		for _ in range(self._nombre_iterations):
			# Générer un voisin
			currentTarget = self.evalTarget(currentSolution)
			self._logger.debug("Objectif actuel : %.2f", currentTarget)

			voisin = self.equipmentSwap(currentSolution)

			# Calculer les objectifs pour la solution actuelle et le voisin
			neightbourgTarget = self.evalTarget(voisin)
			self._logger.debug("Objectif voisin : %2.f", neightbourgTarget)

			# Accepter le voisin si son objectif est meilleur ou si la consommation totale n'excède pas la production solaire
			if neightbourgTarget < currentTarget:
				self._logger.debug("---> On garde l'objectif voisin")
				currentSolution = voisin
				if neightbourgTarget < self.evalTarget(bestSolution):
					self._logger.debug("---> C'est la meilleure jusque là")
					bestSolution = voisin
					bestTarget = neightbourgTarget
			else:
				# Accepter le voisin avec une certaine probabilité
				probabilite = math.exp(
					(currentTarget - neightbourgTarget) / temperature
				)
				if (seuil := random.random()) < probabilite:
					currentSolution = voisin
					self._logger.debug(
							"---> On garde l'objectif voisin car seuil (%.2f) inférieur à proba (%.2f)",
							seuil,
							probabilite,
						)
				else:
					self._logger.debug("--> On ne prend pas")

			# Réduire la température
			temperature *= self._coolingFactor
			self._logger.debug(" !! Temperature %.2f", temperature)
			if temperature < self._temperature_minimale:
				break

		return (
			bestSolution,
			bestTarget,
			self.devicesConsumption(bestSolution),
		)

	def evalTarget(self, solution) -> float:
		"""Calcul de l'objectif : minimiser le surplus de production solaire
		rejets = 0 if consommation_net >=0 else -consommation_net
		consommation_solaire = min(production_solaire, production_solaire - rejets)
		consommation_totale = consommation_net + consommation_solaire
		"""

		puissance_totale_eqt = self.devicesConsumption(solution)
		_totalPowerOfTotalEqtDiff = (
			puissance_totale_eqt - self._totalPowerOfInitialEqt
		)

		newNetConsumption = self._notConsumption + _totalPowerOfTotalEqtDiff
		newDischarges = 0 if newNetConsumption >= 0 else -newNetConsumption
		new_import = 0 if newNetConsumption < 0 else newNetConsumption
		newSolarConsumption = min(
			self._productionSolaire, self._productionSolaire - newDischarges
		)
		newTotalConsumption = (
			newNetConsumption + newDischarges
		) + newSolarConsumption
		self._logger.debug(
				"Objectif : cette solution ajoute %.3fW a la consommation initial. Nouvelle consommation nette=%.3fW. Nouveaux rejets=%.3fW. Nouvelle conso totale=%.3fW",
				_totalPowerOfTotalEqtDiff,
				newNetConsumption,
				newDischarges,
				newTotalConsumption,
			)

		forcedSellCost = self._sellCost * (1.0 - self._sellTax / 100.0)
		importCoefs = (self._buyCost) / (self._buyCost + forcedSellCost)
		dischargesCoefs = (forcedSellCost) / (self._buyCost + forcedSellCost)

		return importCoefs * new_import + dischargesCoefs * newDischarges

	def genererateInitialeSolution(self, solution):
		"""Generate the initial solution (which is the solution given in argument) and calculate the total initial power"""
		self._totalPowerOfInitialEqt = self.devicesConsumption(solution)
		return copy.deepcopy(solution)

	def devicesConsumption(self, solution):
		"""The total power consumption for all active equipement"""
		return sum(
			equipement["requested_power"]
			for equipement in solution
			if equipement["state"]
		)

	def evalNewPower(
		self, currentPower, powerStep, powerMin, powerMax, canSwitchOff
	):
		"""Calculate a new power"""
		choices = []
		powerMinToUse = powerMin if canSwitchOff else powerMin + powerStep
		if currentPower > powerMinToUse:
			choices.append(-1)
		if currentPower < powerMax:
			choices.append(1)

		if len(choices) <= 0:
			# No changes
			return currentPower

		powerAdd = random.choice(choices) * powerStep
		self._logger.debug("Adding %d power to currentPower (%d)", powerAdd, currentPower)
		requestedPower = currentPower + powerAdd
		self._logger.debug("New requestedPower is %s", requestedPower)
		return requestedPower
		# if requestedPower < powerMin:
		# deactivate the equipment
		#    requestedPower = 0
		# elif requestedPower > powerMax:
		# Do nothing
		#    requestedPower = currentPower

	def equipmentSwap(self, solution):
		"""Permuter le state d'un equipement eau hasard"""
		voisin = copy.deepcopy(solution)

		usable = [eqt for eqt in voisin if eqt["is_usable"]]

		if len(usable) <= 0:
			return voisin

		eqt = random.choice(usable)

		# name = eqt["name"]
		state = eqt["state"]
		canChangePower = eqt["canChangePower"]
		isWaiting = eqt["isWaiting"]

		# Current power is the last requested_power
		current_power = eqt.get("requested_power")
		powerMax = eqt.get("powerMax")
		powerStep = eqt.get("powerStep")
		if canChangePower:
			powerMin = eqt.get("powerMin")
		else:
			# If power is not manageable, min = max
			powerMin = powerMax

		# On veut gérer le isWaiting qui interdit d'allumer ou éteindre un eqt usable.
		# On veut pouvoir changer la puissance si l'eqt est déjà allumé malgré qu'il soit waiting.
		# Usable veut dire qu'on peut l'allumer/éteindre OU qu'on peut changer la puissance

		# if not canChangePower and isWaiting:
		#    -> on ne fait rien (mais ne devrait pas arriver car il ne serait pas usable dans ce cas)
		#
		# if state and canChangePower and isWaiting:
		#    -> change power mais sans l'éteindre (requested_power >= powerMin)
		#
		# if state and canChangePower and not isWaiting:
		#    -> change power avec extinction possible
		#
		# if not state and not isWaiting
		#    -> allumage
		#
		# if state and not isWaiting
		#    -> extinction
		#
		if (not canChangePower and isWaiting) or (
			not state and canChangePower and isWaiting
		):
			self._logger.debug("not canChangePower and isWaiting -> do nothing")
			return voisin

		if state and canChangePower and isWaiting:
			# calculated a new power but do not switch off (because waiting)
			requested_power = self.evalNewPower(
				current_power, powerStep, powerMin, powerMax, can_switch_off=False
			)
			assert (
				requested_power > 0
			), "Requested_power should be > 0 because isWaiting is True"

		elif state and canChangePower and not isWaiting:
			# change power and accept switching off
			requested_power = self.evalNewPower(
				current_power, powerStep, powerMin, powerMax, can_switch_off=True
			)
			if requested_power <= powerMin:
				# deactivate the equipment
				eqt["state"] = False
				requested_power = 0

		elif not state and not isWaiting:
			# Allumage
			eqt["state"] = not state
			requested_power = powerMin

		elif state and not isWaiting:
			# Extinction
			eqt["state"] = not state
			requested_power = 0

		elif "requested_power" not in locals():
			self._logger.error("We should not be there. eqt=%s", eqt)
			assert False, "Requested power n'a pas été calculé. Ce n'est pas normal"

		eqt["requested_power"] = requested_power

		self._logger.debug(
				"      -- On permute %s puissance max de %.2f. Il passe à %s",
				eqt["name"],
				eqt["requested_power"],
				eqt["state"],
			)
		return voisin
