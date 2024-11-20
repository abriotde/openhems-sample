#!/usr/bin/env python3
"""
This is the server thread witch aim to centralize information and take right deccisions
"""
import os
import time
from openhems.modules.energy_strategy import OffPeakStrategy
from openhems.modules.util.configuration_manager import ConfigurationManager


class OpenHEMSServer:
	"""
	This is the server thread witch aim to centralize information
	 and take right deccisions to optimize consumption
	"""

	def __init__(self, mylogger, network, serverConf:ConfigurationManager) -> None:
		self.logger = mylogger
		self.network = network
		self.loopDelay = serverConf.get("server.loopDelay")
		strategies = serverConf.get("server.strategy")
		for strategy in strategies:
			stratType = strategy.type
			if stratType=="offpeak":
				params = [p.split("-") for p in strategy.get("params", "[22h-6h]")]
				self.strategies.append(OffPeakStrategy(mylogger, self.network, params))
			elif stratType=="emhass":
				# pylint: disable=import-outside-toplevel
				# Avoid to import EmhassStrategy and all it's dependances when no needs.
				from openhems.modules.energy_strategy.emhass_strategy import EmhassStrategy
				self.strategies.append(EmhassStrategy(mylogger, self.network, serverConf, strategy))
			elif stratType=="range":
				self.strategies.append(RangeStrategy(mylogger, self.network, strategy))
			else:
				self.logger.critical("OpenHEMSServer() : Unknown strategy '%s'", strategy)
			os._exit(1)

	def loop(self, loopDelay):
		"""
		It's the content of each loop.
		If loop delay=0, we consider that we never sleep (For test or reactivity).
		"""
		self.logger.debug("OpenHEMSServer.loop()")
		self.network.updateStates()
		allowSleep = len(self.strategies)<=1
		for strategy in self.strategies:
			strategy.updateNetwork(loopDelay, allowSleep)

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
			self.loop(loopDelay)
			t = time.time()
			if t<nextloop:
				self.logger.debug("OpenHEMSServer.run() : sleep(%f min)", (nextloop-t)/60)
				time.sleep(nextloop-t)
				t = time.time()
			elif t>nextloop:
				self.logger.warning("OpenHomeEnergyManagement::run() "
					": missing time for loop : %d seconds", (nextloop-t))
			nextloop = t + loopDelay
