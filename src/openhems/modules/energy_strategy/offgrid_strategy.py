"""
Case off-grid: minimize battery solicitation
"""

import logging
from openhems.modules.network.network import OpenHEMSNetwork
from .solarbased_strategy import SolarBasedStrategy, GeoPosition

class OffGridStrategy(SolarBasedStrategy):
	"""
	Case off-grid: minimize battery solicitation
	"""

	# pylint: disable=unused-argument
	# pylint: disable=unused-variable
	def __init__(self, network: OpenHEMSNetwork, geoposition: GeoPosition, config):
		super().__init__(network, geoposition, offpeakHoursRanges=[])
		self.logger = logging.getLogger(__name__)
		self.logger.info("OffGridStrategy()")
		self.network = network
		self.checkRange()
		self.maxBatteryLevel = config.get("maxBattery", 95)
		self.hightBatteryLevel = config.get("hightBattery", 80)
		self.lowBatteryLevel = config.get("lowBattery", 20)
		self.minBatteryLevel = config.get("minBattery", 5)

	def updateNetwork(self, cycleDuration):
		batteryLevel = self.network.getBatteryLevel()
		solarProduction = self.network.getSolarProduction()
		return True
