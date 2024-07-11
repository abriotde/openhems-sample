#!/usr/bin/env python3
import time
import re
from datetime import datetime
import yaml
from energy_strategy import EnergyStrategy
from home_assistant_api import HomeAssistantAPI
from energy_strategy import OffPeakStrategy

class OpenHEMSServer:

	def __init__(self, yaml_conf: str) -> None:
		
		with open(yaml_conf, 'r') as file:
			print("Load YAML configuration from '"+yaml_conf+"'")
			self.conf = yaml.load(file, Loader=yaml.FullLoader)
			serverConf = self.conf['server']
			networkUpdater = None
			networkSource = serverConf["network"].lower()
			if networkSource=="homeassistant":
				networkUpdater = HomeAssistantAPI(self.conf)
			else:
				print("ERROR : OpenHEMSServer() : Unknown strategy '",strategy,"'")
				exit(1)
			self.network = networkUpdater.getNetwork()
			self.loop_delay = serverConf["loop_delay"]
			strategy = serverConf["strategy"].lower()
			strategy_params = serverConf["strategy_params"]
			if strategy=="offpeak":
				params = [p.split("-") for p in strategy_params]
				self.strategy = OffPeakStrategy(self.network, params)
			else:
				print("ERROR : OpenHEMSServer() : Unknown strategy '",strategy,"'")
				exit(1)

	def loop(self):
		print("OpenHEMSServer.loop()")
		self.network.updateStates()
		self.strategy.updateNetwork()

	# Run an infinite loop where each loop shouldn't last more than loop_delay and will never last less than loop_delay
	def run(self, loop_delay=0):
		if loop_delay==0:
			loop_delay = self.loop_delay
		nextloop = time.time() + loop_delay
		while True:
			self.loop()
			t = time.time()
			if t<nextloop:
				print("OpenHEMSServer.run() : sleep(",(nextloop-t)/60," min)")
				time.sleep(nextloop-t)
				t = time.time()
			elif t>nextloop:
				print("Warning : OpenHomeEnergyManagement::run() : missing time for loop : ", (t-nextloop), "seconds")
			nextloop = t + loop_delay

