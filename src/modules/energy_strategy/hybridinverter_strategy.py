from datetime import datetime, timedelta
import time
import re
import logging
from modules.network.network import OpenHEMSNetwork
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

	def __init__(self, network: OpenHEMSNetwork):
		logging.getLogger("HybridInverterStrategy").error("SolarOnlyProductionStrategy() : TODO")
		# TODO
	def updateNetwork(self, cycleDuration):
		logging.getLogger("HybridInverterStrategy").error("SolarOnlyProductionStrategy.updateNetwork() : TODO")
		pass
		# TODO

