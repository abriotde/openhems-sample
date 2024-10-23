"""
Case dual-source managed by controlled "source inverter" :
- Solar pannel with micro-inverter
- Grid
Strategy is to :
Advantages : Try no electricity goes in grid.
Disadvantages : 
"""

import logging
from openhems.modules.network.network import OpenHEMSNetwork
from .solarbased_strategy import SolarBasedStrategy

class SolarNoSellStrategy(SolarBasedStrategy):
	"""
	Case dual-source managed by controlled "source inverter" :
	- Solar pannel with micro-inverter
	- Grid
	Strategy is to :
	Advantages : Try no electricity goes in grid.
	Disadvantages : 
	"""

	# pylint: disable=unused-argument
	def __init__(self, network: OpenHEMSNetwork, gridId:str, inverterId:str, 
			config, latitude, longitude, offpeakHoursRanges):
		self.logger = logging.getLogger(__name__)
		super().__init__(network, latitude, longitude, offpeakHoursRanges)
		self.logger.info("SolarNoSellStrategy()")
		self.network = network
		self.checkRange()
		self.maxBatteryLevel = config.get("maxBattery", 95)
		self.hightBatteryLevel = config.get("hightBattery", 80)
		self.lowBatteryLevel = config.get("lowBattery", 20)
		self.minBatteryLevel = config.get("minBattery", 5)

	def updateNetwork(self, cycleDuration):
		return True
