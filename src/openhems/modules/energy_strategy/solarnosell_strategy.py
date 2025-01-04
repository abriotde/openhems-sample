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
from .solarbased_strategy import SolarBasedStrategy, GeoPosition

class SolarNoSellStrategy(SolarBasedStrategy):
	"""
	Case dual-source managed by controlled "source inverter" :
	- Solar pannel with micro-inverter
	- Grid
	Strategy is to :
	Advantages : Try no electricity goes in grid.
	Disadvantages : 
	"""

	def __init__(self, network: OpenHEMSNetwork,
			config, geoPosition: GeoPosition, offpeakHoursRanges):
		del offpeakHoursRanges, config
		self.logger = logging.getLogger(__name__)
		super().__init__(network, geoPosition)
		self.logger.info("SolarNoSellStrategy()")
		self.network = network

	def updateNetwork(self, cycleDuration:int, allowSleep:bool, now=None):
		# TODO
		return True
