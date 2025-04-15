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
from .optimization_algorithm import OptimizationAlgorithm, Algorithme
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
		self._algo = OptimizationAlgorithm(
			initTemp, minTemp, coolingFactor, maxIterationNumber, logger=self.logger, algo=Algorithme.GENETIC
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
		powerConsumption = sum(node.getCurrentPower() for node in self.network.getAll("publicpowergrid"))
		powerProduction = sum(node.getCurrentPower() for node in self.network.getAll("solarpanel"))
		batteries = self.network.getAll("battery")
		# TODO : create dedicated function for battery in network
		if len(batteries):
			# TODO : improve accuracy (It's wrong)
			batterySoc = sum(node.getLevel() for node in batteries) / len(batteries)
		else:
			batterySoc = 0
		buyCost = self.network.getPrice()
		sellCost = self.network.getSellPrice()
		offpeakPrice = self.network.getHoursRanges().getOffpeakPrice()
		# sellTaxPercent = 100 * (buyCost - sellCost) / buyCost if buyCost != 0 else 0
		nodes = self.getNodes()
		for node in nodes:
			self.deferables[node.id] = node
		self._bestSolution, self._bestGoal, self._totalPower \
			= self._algo.run(
			nodes,
			powerConsumption,
			powerProduction,
			sellCost,
			buyCost,
			batterySoc,
			offpeakPrice
		)

	def apply(self, cycleDuration, now=None):
		"""
		This apply what eval function computed.
		"""
		del now
		nodes = [(node.name+"="+str(node.requestedPower)) for node in self._bestSolution if node.isUsable]
		self.logger.debug("Apply %s", nodes)
		# Uses the result to turn on or off or change power
		for equipment in self._bestSolution:
			nodeId = equipment.name
			requestedPower = equipment.requestedPower
			node = self.deferables.get(nodeId)
			if node is None:
				continue
			state = requestedPower>0
			self.switchSchedulable(node, state)

			# Send change power if state is now on and change power is accepted and
			#  (power have change or eqt is just activated)
			if (state and node.isControlledPower()
				and (node.getCurrentPower() != requestedPower)
				 # TODO : Warning maybe we don't set power but an abstract value...
			):
				self.logger.debug("Change power of %s to %s", equipment.name, requestedPower)
				# TODO, there is no variable devices in OpenHEMS today
				node.setControlledPower(requestedPower)
		return cycleDuration
