#!/usr/bin/env python3

import logging
import time
import re
from datetime import datetime
from modules.energy_strategy import EnergyStrategy,OffPeakStrategy


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
			exit(1)

	def loop(self, loop_delay):
		self.logger.debug("OpenHEMSServer.loop()")
		self.network.updateStates()
		self.strategy.updateNetwork(loop_delay)

	# Run an infinite loop where each loop shouldn't last more than loop_delay and will never last less than loop_delay
	def run(self, loop_delay=0):
		if loop_delay==0:
			loop_delay = self.loop_delay
		nextloop = time.time() + loop_delay
		while True:
			self.loop(loop_delay)
			t = time.time()
			if t<nextloop:
				self.logger.debug("OpenHEMSServer.run() : sleep("+str((nextloop-t)/60)+" min)")
				time.sleep(nextloop-t)
				t = time.time()
			elif t>nextloop:
				self.logger.warning("OpenHomeEnergyManagement::run() : missing time for loop : "+str((nextloop-t))+" seconds")
			nextloop = t + loop_delay

