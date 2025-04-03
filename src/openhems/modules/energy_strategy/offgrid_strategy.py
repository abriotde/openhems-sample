"""
Case off-grid: minimize battery solicitation

#TODO : Implemented - Call - Conf - TestAuto - RunOk - InProd : 0/6
"""

import logging
from openhems.modules.network.network import OpenHEMSNetwork
from .solarbased_strategy import SolarBasedStrategy, GeoPosition

class OffGridStrategy(SolarBasedStrategy):
	"""
	Case off-grid: minimize battery solicitation
	"""

	def __init__(self, strategyId:str, network: OpenHEMSNetwork, geoposition: GeoPosition, config):
		super().__init__(strategyId, network, geoposition)
		self.logger = logging.getLogger(__name__)
		self.logger.info("OffGridStrategy()")
		self.network = network
		self.maxBatteryLevel = config.get("maxBattery", 95)
		self.hightBatteryLevel = config.get("hightBattery", 80)
		self.lowBatteryLevel = config.get("lowBattery", 20)
		self.minBatteryLevel = config.get("minBattery", 5)

	def updateNetwork(self, cycleDuration:int, now=None):
		del cycleDuration, now
		# batteryLevel = self.network.getBatteryLevel()
		# solarProduction = self.network.getSolarProduction()
		# TODO
		return True
