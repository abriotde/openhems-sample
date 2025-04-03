"""
Case dual-source managed by controlled "hybrid inverter with security mode" :
- Solar pannel
- batterie
- Grid : disabled if off by the inverter
Strategy is to minimize load/unload battery and minimize grid consumption
Advantages : 
Disadvantages : 

TODO : Implemented - Call - Conf - TestAuto - RunOk - InProd : 6/6
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

	def __init__(self, strategyId:str, network:OpenHEMSNetwork, geoposition:GeoPosition):
		super().__init__(strategyId, network, geoposition)
		logging.getLogger("HybridInverterStrategy")\
			.error("SolarOnlyProductionStrategy() : TODO")
		# TODO

	def updateNetwork(self, cycleDuration:int, now=None):
		del cycleDuration, now
		logging.getLogger("HybridInverterStrategy")\
			.error("SolarOnlyProductionStrategy.updateNetwork() : TODO")
		# TODO
