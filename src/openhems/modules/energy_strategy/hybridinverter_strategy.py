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
from .solarbased_strategy import SolarBasedStrategy

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

	def __init__(self, network: OpenHEMSNetwork, latitude, longitude):
		super().__init__(network, latitude, longitude, offpeakHoursRanges=[])
		logging.getLogger("HybridInverterStrategy")\
			.error("SolarOnlyProductionStrategy() : TODO")
		# TODO
	def updateNetwork(self, cycleDuration):
		logging.getLogger("HybridInverterStrategy")\
			.error("SolarOnlyProductionStrategy.updateNetwork() : TODO")
		# TODO
