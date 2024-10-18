from datetime import datetime, timedelta
import time
import re
import logging
from modules.network.network import OpenHEMSNetwork
from .solarbased_strategy import SolarBasedStrategy

class OffGridStrategy(SolarBasedStrategy):
	"""
	Case off-grid: minimize battery solicitation
	"""


	def __init__(self, network: OpenHEMSNetwork, gridId:str, inverterId:str, config):
		self.logger = logging.getLogger(__name__)
		self.logger.info("OffGridStrategy("+str(offpeakHoursRanges)+")")
		self.network = network
		self.setOffPeakHoursRanges(offpeakHoursRanges)
		self.checkRange()
		self.maxBatteryLevel = config.get("maxBattery", 95)
		self.hightBatteryLevel = config.get("hightBattery", 80)
		self.lowBatteryLevel = config.get("lowBattery", 20)
		self.minBatteryLevel = config.get("minBattery", 5)

	def updateNetwork(self, cycleDuration):
		
		batteryLevel = self.network.getBatteryLevel()
		solarProduction = self.network.getSolarProduction()
		return True

