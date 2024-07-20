#!/usr/bin/env python3

import time
import re
from datetime import datetime
from energy_strategy import EnergyStrategy,OffPeakStrategy

class OpenHEMSServer:

	def __init__(self, network, serverConf) -> None:
		self.network = network
		self.loop_delay = serverConf["loop_delay"]
		strategy = serverConf["strategy"].lower()
		strategy_params = serverConf["strategy_params"]
		if strategy=="offpeak":
			params = [p.split("-") for p in strategy_params]
			self.strategy = OffPeakStrategy(self.network, params)
		else:
			print("ERROR : OpenHEMSServer() : Unknown strategy '",strategy,"'")
			exit(1)

	def loop(self, loop_delay):
		print("OpenHEMSServer.loop()")
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
				print("OpenHEMSServer.run() : sleep(",(nextloop-t)/60," min)")
				time.sleep(nextloop-t)
				t = time.time()
			elif t>nextloop:
				print("Warning : OpenHomeEnergyManagement::run() : missing time for loop : ", (t-nextloop), "seconds")
			nextloop = t + loop_delay

