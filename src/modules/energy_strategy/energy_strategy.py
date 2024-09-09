from datetime import datetime, timedelta
import time
import re
import logging
from modules.network.network import OpenHEMSNetwork

class EnergyStrategy:
	def  __init__(self):
		pass

	def updateNetwork(self):
		logging.getLogger("EnergyStrategy").error("EnergyStrategy.updateNetwork() : To implement in sub-class")

