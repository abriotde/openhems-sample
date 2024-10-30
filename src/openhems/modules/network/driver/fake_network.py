"""
This is a fake network for tests.
  Values are set random
  or from specific data set.
"""

import os
import re
import logging
import datetime
import time
import requests
import yaml
from openhems.modules.network.network import OpenHEMSNetwork, HomeStateUpdater
from openhems.modules.network.network import POWER_MARGIN
from openhems.modules.network.feeder import Feeder, RandomFeeder, ConstFeeder, RotationFeeder
from openhems.modules.network.node import PublicPowerGrid, SolarPanel, Battery, OutNode

regexpFloat = re.compile("^[0-9]+(.[0-9]+)?$")
regexpRandomFeeder = re.compile("^RANDOM(([0-9]+(.[0-9]+)?) *, *([0-9]+(.[0-9]+)?) *, *([0-9]+(.[0-9]+)?) *)$")
todays_Date = datetime.date.fromtimestamp(time.time())
date_in_ISOFormat = todays_Date.isoformat()

class HATypeExcetion(Exception):
	"""
	Custom Home-Assitant excepton to be captured.
	"""
	def __init__(self):
		self.message = message
		self.defaultValue = defaultValue

class FakeNetwork(HomeStateUpdater):

	def __init__(self, conf) -> None:
		super().__init__(conf)

	def getFeeder(self, conf, kkey, default_value=None) -> Feeder:
		"""
		Return a feeder considering
		 if the "kkey" can be a Home-Assistant element id.
		 Otherwise, it consider it as constant.
		"""
		feeder = None
		key = conf.get(kkey, None)
		if isinstance(key, str):
			key = key.strip().upper()
			if regexpFloat.match(key):
				self.logger.info("ConstFeeder(%s)", key)
				feeder = ConstFeeder(float(key))
			elif regexpRandomFeeder.match(key):
				vals = regexpRandomFeeder.match(key)
				self.logger.info("RandomFeeder(%s)", key)
				feeder = RandomFeeder(self, float(vals[1]), float(vals[2]), float(vals[3]))
		elif isinstance(key, list):
			self.logger.info("RotationFeeder(%s)", key)
			feeder = RotationFeeder(self, key)
		elif default_value is not None:
			self.logger.info("ConstFeeder(%s)", default_value)
			feeder = ConstFeeder(default_value)
		else:
			self.logger.info("ConstFeeder(%s)", key)
			feeder = ConstFeeder(key)
		return feeder

	def getNetworkIn(self, network_conf):
		"""
		Initialyze "in" network part.
		"""
		# init Feeders
		for e in network_conf["in"]:
			classname = e["class"].lower()
			currentPower = self.getFeeder(e, "currentPower")
			powerMargin = self.getFeeder(e, "powerMargin", POWER_MARGIN)
			maxPower = self.getFeeder(e, "maxPower")
			minPower = self.getFeeder(e, "minPower", 0)
			node = None
			if classname == "publicpowergrid":
				node = PublicPowerGrid(currentPower, maxPower, minPower, powerMargin)
			elif classname == "solarpanel":
				node = SolarPanel(currentPower, maxPower, minPower, powerMargin)
			elif classname == "battery":
				lowLevel = self.getFeeder(e, "lowLevel",
					ha_elements, "int", POWER_MARGIN)
				hightLevel = self.getFeeder(e, "hightLevel",
					ha_elements, "int", POWER_MARGIN)
				capacity = self.getFeeder(e, "capaciity",
					ha_elements, "int", POWER_MARGIN)
				currentLevel = self.getFeeder(e, "level", ha_elements, "int", 0)
				node = Battery(currentPower, maxPower, powerMargin, capacity,
					currentLevel ,minPower=minPower, lowLevel=lowLevel,
					hightLevel=hightLevel)
			else:
				self.logger.critical("HomeAssistantAPI.getNetwork : "
					"Unknown classname '{classname}'")
				os._exit(1)
			if "id" in e.keys():
				node.id = e["id"]
			# print(node)
			self.network.addNode(node)

	def getNetworkOut(self, network_conf):
		"""
		Initialyze "out" network part.
		"""
		i = 0
		for e in network_conf["out"]:
			classname = e["class"].lower()
			node = None
			HAid = e.get("id", f"node_{i}")
			i += 1
			if classname == "switch":
				currentPower = self.getFeeder(e, "currentPower")
				isOn = self.getFeeder(e, "isOn")
				maxPower = self.getFeeder(e, "maxPower", 2000)
				node = OutNode(HAid, currentPower, maxPower, isOn)
			else:
				self.logger.critical("HomeAssistantAPI.getNetwork : "
					"Unknown classname '{classname}'")
				os._exit(1)
			# print(node)
			self.network.addNode(node)

	def getNetwork(self) -> OpenHEMSNetwork:
		"""
		Explore the home device network available with Home-Assistant.
		"""
		super().getNetwork()
		network_conf = self.conf["network"]
		self.getNetworkIn(network_conf)
		self.getNetworkOut(network_conf)
		self.network.print(self.logger.info)
		return self.network

	def updateNetwork(self):
		"""
		Update network, but as it's a fake one, we need a way to determine it:
		* Random
		* from Dataset
		"""
		super().updateNetwork()
		
