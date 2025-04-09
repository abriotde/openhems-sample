#!/usr/bin/env python3
"""
This HomeStateUpdater is based on home-Assistant software. 
It access to this by the API using URL and long_lived_token
"""

import os
import time
import json
import requests
from openhems.modules.network import (
	HomeStateUpdater, HomeStateUpdaterException
)
from openhems.modules.network.feeder import Feeder, SourceFeeder, ConstFeeder
from openhems.modules.util.cast_utility import CastUtililty, CastException
from openhems.modules.util.configuration_manager import ConfigurationManager, ConfigurationException

class HATypeExcetion(Exception):
	"""
	Custom Home-Assitant excepton to be captured.
	"""
	def __init__(self, message, defaultValue):
		self.message = message
		self.defaultValue = defaultValue

class DomoticzAPI(HomeStateUpdater):
	"""
	Domoticz is a C++ implementation
	This HomeStateUpdater is based on Domoticz software.
	It access to this by the API using URL and long_lived_token
	Doc : https://wiki.domoticz.com/Domoticz_API/JSON_URL%27s

	* Jeedom/Nextdom : PHP implementation
	https://doc.jeedom.com/fr_FR/core/4.2/api_http

	* OpenHAB : Java implementation
	https://www.openhab.org/docs/configuration/restdocs.html
	"""
	def __init__(self, conf:ConfigurationManager) -> None:
		super().__init__(conf)
		self.token = os.getenv("SUPERVISOR_TOKEN") # Injected by Supervisor on Home-Assistant OS
		if self.token is None:
			self.apiUrl = conf.get("api.url")
			self.token = conf.get("api.long_lived_token")
		else:
			self.apiUrl = "http://supervisor/core/api"
		self._elemsKeysCache = None
		self.cachedIds = {}
		# Time to sleep after wrong HomeAssistant call
		self.sleepDurationOnerror = 2
		self.network = None
		self.haElements = None

	def initNetwork(self, network):
		"""
		Get all nodes according to Home-Assistants
		"""
		# TODO

	def updateNetwork(self):
		"""
		Update network, but as we ever know it's architecture,
		 we just have to update few values.
		"""
		# TODO
		super().updateNetwork()
		return True


	# pylint: disable=too-many-branches
	def callAPI(self, url: str, data=None):
		"""
		Call Home-Assistant API.
		"""
		# TODO