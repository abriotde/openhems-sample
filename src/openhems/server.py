#!/usr/bin/env python3
"""
This is the server thread witch aim to centralize information and take right deccisions
"""
import time
import datetime
from openhems.modules.energy_strategy import OffPeakStrategy, SwitchoffStrategy, LOOP_DELAY_VIRTUAL
from openhems.modules.network import HomeStateUpdaterException
from openhems.modules.util import CastUtililty
from openhems.modules.util.configuration_manager import ConfigurationManager, ConfigurationException


class OpenHEMSServer:
	"""
	This is the server thread witch aim to centralize information
	 and take right deccisions to optimize consumption
	"""

	def __init__(self, mylogger, network, serverConf:ConfigurationManager) -> None:
		self.logger = mylogger
		self.network = network
		self.loopDelay = serverConf.get("server.loopDelay")
		strategies = serverConf.get("server.strategies")
		self.strategies = []
		throwErr = None
		for strategyParams in strategies:
			strategy = strategyParams.get("class", "")
			strategyId = strategyParams.get("id", strategy)
			if strategy=="offpeak":
				self.strategies.append(OffPeakStrategy(mylogger, self.network, strategyId))
			elif strategy=="switchoff":
				offhoursrange = strategyParams.get('offrange', "[22h-6h]")
				condition = strategyParams.get('condition', True)
				reverse = CastUtililty.toTypeBool(strategyParams.get('reverse', False))
				strategyObj = SwitchoffStrategy(mylogger, self.network, strategyId,
				                                offhoursrange, reverse, condition)
				self.strategies.append(strategyObj)
			elif strategy=="emhass":
				# pylint: disable=import-outside-toplevel
				# Avoid to import EmhassStrategy and all it's dependances when no needs.
				from openhems.modules.energy_strategy.emhass_strategy import EmhassStrategy
				self.strategies.append(EmhassStrategy(mylogger, self.network, serverConf, strategyId))
			else:
				msg = f"OpenHEMSServer() : Unknown strategy '{strategy}'"
				self.logger.critical(msg)
				throwErr = msg
		if throwErr is not None:
			raise ConfigurationException(throwErr)
		self.allowSleep = len(self.strategies)==1

	def getSchedule(self):
		"""
		Return scheduled planning.
		"""
		schedule = {}
		for strategy in self.strategies:
			nodes = strategy.getSchedulableNodes()
			for node in nodes:
				myid = node.id
				sc = node.getSchedule()
				if sc is not None:
					schedule[myid] = sc
		return schedule

	def loop(self, loopDelay, now=None):
		"""
		It's the content of each loop.
		If loop delay=0, we consider that we never sleep (For test or reactivity).
		"""
		if now is None:
			now = datetime.datetime.now()
		self.logger.debug("OpenHEMSServer.loop()")
		self.network.updateStates()
		time2wait = 86400
		allowSleep = self.allowSleep and loopDelay>LOOP_DELAY_VIRTUAL
		for strategy in self.strategies:
			t = strategy.updateNetwork(loopDelay, allowSleep, now)
			time2wait = min(t, time2wait)
		if allowSleep and time2wait > 0:
			self.logger.info("Loop sleep(%d min)", round(time2wait/60))
			time.sleep(time2wait)

	def run(self, loopDelay=0):
		"""
		Run an infinite loop
		 where each loop shouldn't last more than loopDelay
		 and will never last less than loopDelay
		If loop delay=0, we consider that we never sleep (For test or reactivity).
		"""
		if loopDelay==0:
			loopDelay = self.loopDelay
		nextloop = time.time() + loopDelay
		while True:
			try:
				self.loop(loopDelay)
			except (HomeStateUpdaterException, ConfigurationException) as e:
				msg = ("Fail update network. Maybe Home-Assistant is down"
					" or long_lived_token expired. "+str(e))
				self.logger.error(msg)
			t = time.time()
			if t<nextloop:
				self.logger.debug("OpenHEMSServer.run() : sleep(%f min)", (nextloop-t)/60)
				time.sleep(nextloop-t)
				t = time.time()
			elif t>nextloop:
				self.logger.warning("OpenHomeEnergyManagement::run() "
					": missing time for loop : %d seconds", (nextloop-t))
			nextloop = t + loopDelay
