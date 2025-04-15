#!/usr/bin/env python3
"""
This HomeStateUpdater is based on home-Assistant software. 
It access to this by the API using URL and long_lived_token
"""

from openhems.modules.network import HomeStateUpdater
from openhems.modules.util.configuration_manager import ConfigurationManager

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
		print("DomoticzAPI.__init__() : TODO")
		# TODO

	def initNetwork(self, network):
		"""
		Get all nodes according to Home-Assistants
		"""
		del network
		print("DomoticzAPI.initNetwork() : TODO")
		# TODO

	def updateNetwork(self):
		"""
		Update network, but as we ever know it's architecture,
		 we just have to update few values.
		"""
		# TODO
		super().updateNetwork()
		print("DomoticzAPI.updateNetwork() : TODO")
		return True


	# pylint: disable=too-many-branches
	def callAPI(self, url: str, data=None):
		"""
		Call Home-Assistant API.
		"""
		# TODO
