"""
This is a similar use case of EMHASS strategy, but without IA usage.
The advantage is to conssume less resources, but the disadvantage is to be maybe less accurate.
This strategy is based on a simulated annealing algorithm https://en.wikipedia.org/wiki/Simulated_annealing.
It's inspired by https://github.com/jmcollin78/solar_optimizer.git
"""

import logging
from datetime import datetime, timedelta
from openhems.modules.network.network import OpenHEMSNetwork
from .simulated_annealing_algo import SimulatedAnnealingAlgorithm
from .energy_strategy import EnergyStrategy, LOOP_DELAY_VIRTUAL

TIMEDELTA_0 = timedelta(0)

# pylint: disable=broad-exception-raised
class SimulatedAnnealingStrategy(EnergyStrategy):
	"""
	short name is AnnealingStrategy
	"""

	def __init__(self, mylogger, network: OpenHEMSNetwork,
			configurationGlobal:ConfigurationManager, configurationAnnealing:dict,
			strategyId:str="emhass"):
		super().__init__(strategyId, network, mylogger, True)
		self.logger.info("SimulatedAnnealingStrategy(%s)", configurationAnnealing)

		init_temp = float(configurationAnnealing.get("initial_temp"))
		min_temp = float(configurationAnnealing.get("min_temp"))
		cooling_factor = float(configurationAnnealing.get("cooling_factor"))
		max_iteration_number = int(configurationAnnealing.get("max_iteration_number"))
		self._algo = SimulatedAnnealingAlgorithm(
			init_temp, min_temp, cooling_factor, max_iteration_number
		)
		self.network = network
		freq = configurationAnnealing.get("freq")
		self.evalFrequence = timedelta(minutes=freq)
		self.timezone = pytz.timezone(configurationGlobal.get("localization.timeZone"))
		self.data = None
		self.deferables = {}
		self.deferablesKeys = []
		self.nextEvalDate = datetime.now(self.timezone) - self.evalFrequence
		self._bestSolution = None
		self._bestGoal = None
		self._totalPower = None

	def eval(self):
		"""
		Eval the best optimization plan using simulated annealing algorithm.
		"""
		powerConsumption = self.network.getCurrentPowerConsumption()
		batteries = self.network.getAll("battery")
		# TODO : create dedicated function for battery in network
		powerProduction = sum(node.getCurrentPower() for node in batteries)
		batterySoc = sum(node.getLevel() for node in batteries) / len(batteries) # TODO : improve accuracy (It's wrong)
		buyCost = self.network.getPrice()
		sellCost = self.network.getSellPrice()
		sellTaxPercent = 100*(buyCost-sellCost)/buyCost

		self._bestSolution, self._bestGoal, self._totalPower \
			= self._algo.simulatedAnnealing(
			self._devices,
			powerConsumption,
			powerProduction,
			sellCost,
			buyCost,
			sellTaxPercent,
			batterySoc
		)

	def apply(self, cycleDuration, now=None):
		"""
		This apply what eval function computed.
		"""
		# Uses the result to turn on or off or change power
		for equipement in self._bestSolution:
			nodeId = equipement["name"]
			requestedPower = equipement.get("requested_power")
			state = equipement["state"]
			device = self.deferables[nodeId]
			if not device:
				continue
			self.switchOnSchedulable(device, cycleDuration, state)

			# Send change power if state is now on and change power is accepted and (power have change or eqt is just activated)
			if (state and device.isControlledPower()
				and (device.getCurrentPower() != requestedPower)
				 # TODO : Warning maybe we don't set power but an abstract value...
			):
				self.logger.debug("Change power of %s to %s", equipement["name"], requestedPower)
				# TODO, there is no variable devices in OpenHEMS today
				device.setControlledPower(requestedPower)

	def updateNetwork(self, cycleDuration, allowSleep:bool, now=None):
		"""
		Decide what to do during the cycle:
		 IF off-peak : switch on all
		 ELSE : Switch off all AND Sleep until off-peak
		Now is used to get a fake 
		"""
		if now is None:
			now = datetime.now(self.timezone)
		elif now.tzinfo is None or now.tzinfo!=self.timezone:
			now = now.replace(tzinfo=self.timezone)
		self.check(now)
		self.apply(cycleDuration, now=now)
		return cycleDuration