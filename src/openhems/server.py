#!/usr/bin/env python3
"""
This is the server thread witch aim to centralize information and take right deccisions
"""
import logging
import os
import time
from openhems.modules.energy_strategy import OffPeakStrategy


class OpenHEMSServer:
	"""
	This is the server thread witch aim to centralize information
	 and take right deccisions to optimize consumption
	"""

	def __init__(self, network, serverConf) -> None:
		self.logger = logging.getLogger(__name__)
		self.network = network
		self.loopDelay = serverConf["loopDelay"]
		strategy = serverConf["strategy"].lower()
		strategyParams = serverConf["strategyParams"]
		if strategy=="offpeak":
			params = [p.split("-") for p in strategyParams]
			self.strategy = OffPeakStrategy(self.network, params)
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
		self.strategy.updateNetwork(loopDelay)

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
