"""
Case dual-source managed by controlled "hybrid inverter with security mode" :
- Solar pannel
- batterie
- Grid : disabled if off by the inverter
Strategy is to minimize load/unload battery and minimize grid consumption
Advantages : 
Disadvantages : 
"""

import logging
from openhems.modules.network.network import OpenHEMSNetwork
from .solarbased_strategy import SolarBasedStrategy, GeoPosition

class HybridInverterStrategy(SolarBasedStrategy):
	"""
	Case dual-source managed by controlled "hybrid inverter with security mode" :
	- Solar pannel
	- batterie
	- Grid : disabled if off by the inverter
	Strategy is to minimize load/unload battery and minimize grid consumption
	Advantages : 
	Disadvantages : 
	"""

	def __init__(self, network: OpenHEMSNetwork, geoposition: GeoPosition, offpeakHoursRanges=None):
		del offpeakHoursRanges
		super().__init__(network, geoposition)
		logging.getLogger("HybridInverterStrategy")\
			.error("SolarOnlyProductionStrategy() : TODO")
		# TODO

	def updateNetwork(self, cycleDuration:int, allowSleep:bool, now=None):
		logging.getLogger("HybridInverterStrategy")\
			.error("SolarOnlyProductionStrategy.updateNetwork() : TODO")
		# TODO
