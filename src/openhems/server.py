#!/usr/bin/env python3

import logging, os
import time
from modules.energy_strategy import OffPeakStrategy


class OpenHEMSServer:

	def __init__(self, network, serverConf) -> None:
		self.logger = logging.getLogger(__name__)
		self.network = network
		self.loop_delay = serverConf["loop_delay"]
		strategy = serverConf["strategy"].lower()
		strategy_params = serverConf["strategy_params"]
		if strategy=="offpeak":
			params = [p.split("-") for p in strategy_params]
			self.strategy = OffPeakStrategy(self.network, params)
		else:
			self.logger.critical("OpenHEMSServer() : Unknown strategy '"+strategy+"'")
			os._exit(1)

	def loop(self, loop_delay):
		"""
		It's the content of each loop.
		"""
		self.logger.debug("OpenHEMSServer.loop()")
		self.network.updateStates()
		self.strategy.updateNetwork(loop_delay)

	def run(self, loop_delay=0):
		"""
		Run an infinite loop
		 where each loop shouldn't last more than loop_delay
		 and will never last less than loop_delay
		"""
		if loop_delay==0:
			loop_delay = self.loop_delay
		nextloop = time.time() + loop_delay
		while True:
			self.loop(loop_delay)
			t = time.time()
			if t<nextloop:
				self.logger.debug("OpenHEMSServer.run() : sleep(%f min)" % (nextloop-t)/60)
				time.sleep(nextloop-t)
				t = time.time()
			elif t>nextloop:
				self.logger.warning("OpenHomeEnergyManagement::run() \
					: missing time for loop : %i seconds" % (nextloop-t))
			nextloop = t + loop_delay
