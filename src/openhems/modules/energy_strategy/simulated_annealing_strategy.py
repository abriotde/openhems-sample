"""
This is a similar use case of EMHASS strategy, but without IA usage.
The advantage is to conssume less resources, but the disadvantage is to be maybe less accurate.
This strategy is based on a simulated annealing algorithm 
https://en.wikipedia.org/wiki/Simulated_annealing.
It's inspired by https://github.com/jmcollin78/solar_optimizer.git

#TODO: RunOk - InProd : 4/6
"""

from datetime import datetime, timedelta
from openhems.modules.network.network import OpenHEMSNetwork
from openhems.modules.util import ConfigurationManager
from .simulated_annealing_algo import SimulatedAnnealingAlgorithm
from .energy_strategy import EnergyStrategy

TIMEDELTA_0 = timedelta(0)

# pylint: disable=broad-exception-raised
class SimulatedAnnealingStrategy(EnergyStrategy):
	"""
	short name is AnnealingStrategy
	"""

	def __init__(self, myLogger, network: OpenHEMSNetwork,
			configurationGlobal:ConfigurationManager, configurationAnnealing: dict,
			strategyId: str = "emhass"):
		del configurationGlobal
		super().__init__(strategyId, network, myLogger)
		self.logger.info("SimulatedAnnealingStrategy(%s)", configurationAnnealing)

		initTemp = float(configurationAnnealing.get("initial_temp"))
		minTemp = float(configurationAnnealing.get("min_temp"))
		coolingFactor = float(configurationAnnealing.get("cooling_factor"))
		maxIterationNumber = int(configurationAnnealing.get("max_iteration_number"))
		self._algo = SimulatedAnnealingAlgorithm(
			initTemp, minTemp, coolingFactor, maxIterationNumber, logger=self.logger
		)
		self.network = network
		freq = configurationAnnealing.get("freq")
		self.evalFrequence = timedelta(minutes=freq)
		self.data = None
		self.nextEvalDate = datetime.now() - self.evalFrequence
		self._bestSolution = None
		self._bestGoal = None
		self._totalPower = None
		self.deferables = {}

	def eval(self):
		"""
		Eval the best optimization plan using simulated annealing algorithm.
		"""
		powerConsumption = self.network.getCurrentPower()
		solarPanel = self.network.getAll("solarpanel")
		powerProduction = sum(node.getCurrentPower() for node in solarPanel)
		powerProduction = 1000
		batteries = self.network.getAll("battery")
		# TODO : create dedicated function for battery in network
		if len(batteries):
			# TODO : improve accuracy (It's wrong)
			batterySoc = sum(node.getLevel() for node in batteries) / len(batteries)
		else:
			batterySoc = 0
		buyCost = self.network.getPrice()
		sellCost = self.network.getSellPrice()
		sellTaxPercent = 100 * (buyCost - sellCost) / buyCost

		nodes = self.getNodes()
		for node in nodes:
			self.deferables[node.id] = node
		self._bestSolution, self._bestGoal, self._totalPower \
			= self._algo.simulatedAnnealing(
			nodes,
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
		del now
		print(self._bestSolution)
		# Uses the result to turn on or off or change power
		for equipment in self._bestSolution:
			nodeId = equipment.name
			requestedPower = equipment.requestedPower
			state = equipment.state
			node = self.deferables.get(nodeId)
			if node is None:
				continue
			self.switchSchedulable(node, cycleDuration, state)

			# Send change power if state is now on and change power is accepted and
			#  (power have change or eqt is just activated)
			if (state and node.isControlledPower()
				and (node.getCurrentPower() != requestedPower)
				 # TODO : Warning maybe we don't set power but an abstract value...
			):
				self.logger.debug("Change power of %s to %s", equipment.name, requestedPower)
				# TODO, there is no variable devices in OpenHEMS today
				node.setControlledPower(requestedPower)

	def updateNetwork(self, cycleDuration, now=None):
		"""
		Decide what to do during the cycle:
		 IF off-peak : switch on all
		 ELSE : Switch off all AND Sleep until off-peak
		Now is used to get a fake 
		"""
		if now is None:
			now = datetime.now()
		self.check(now)
		self.apply(cycleDuration, now=now)
		return cycleDuration
