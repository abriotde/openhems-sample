"""
Class to create a OpenHEMSNetwork using drivers
"""

from openhems.modules.util import (
	ConfigurationManager, ConfigurationException
)
from .driver.home_assistant_api import HomeAssistantAPI
from .driver.fake_network import FakeNetwork
from .network import OpenHEMSNetwork

def getNetworkFromConfiguration(logger, configurator:ConfigurationManager):
	"""
	Method to instantiate a network from a ConfigurationManager 
	"""
	networkSource = configurator.get("server.network")
	if networkSource=="homeassistant":
		logger.info("Network: HomeAssistantAPI")
		networkUpdater = HomeAssistantAPI(configurator)
	elif networkSource=="fake":
		logger.info("Network: FakeNetwork")
		networkUpdater = FakeNetwork(configurator)
	else:
		raise ConfigurationException(f"Invalid server.network configuration '{networkSource}'")
	network = OpenHEMSNetwork(logger, networkUpdater, configurator.get("network.nodes"))
	return network
