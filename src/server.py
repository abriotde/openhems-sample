#!/usr/bin/env python3
import time
import re
from datetime import datetime
import yaml
from energy_strategy import EnergyStrategy
from home_assistant_api import HomeAssistantAPI

class OpenHEMSServer:

	def __init__(self, yaml_conf: str) -> None:
		with open(yaml_conf, 'r') as file:
			print("Load YAML configuration from '"+yaml_conf+"'")
			self.conf = yaml.load(file, Loader=yaml.FullLoader)
			serverConf = self.conf['server']
			self.loop_delay = serverConf["loop_delay"]
			api_manager = HomeAssistantAPI(self.conf)
			self.network = api_manager.getNetwork()

	# Update the home energy state : all changed elements.
	def updateState(self):
		self.network.updateStates()
		# find E demand
		# predict E cost/production
		# 

	def loop(self):
		print("OpenHEMSServer.loop()")
		self.updateState()
		# self

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

