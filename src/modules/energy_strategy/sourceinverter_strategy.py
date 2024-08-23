from datetime import datetime, timedelta
import time
import re
import logging
from modules.network.network import OpenHEMSNetwork
from .solarbased_strategy import SolarBasedStrategy

class SourceInverterStrategy(SolarBasedStrategy):
	"""
	Case dual-source managed by controlled "source inverter" :
	- Solar pannel and batterie managed by MPPT
	- Grid
	Strategy is to :
	- Use grid energy when battery level is low and solar production less than consumption
	- Reverse if battery level is medium and/or solar production higher than conumption
	Advantages : No electricity goes in grid.
	Disadvantages : Could not charge battery on off-peak grid hours if there is- not so much solar production
	"""


	def __init__(self, network: OpenHEMSNetwork, gridId:str, inverterId:str, config):
		self.logger = logging.getLogger(__name__)
		self.logger.info("SourceInverterStrategy("+str(config)+")")
		self.network = network
		self.setOffPeakHoursRanges(offpeakHoursRanges)
		self.checkRange()
		self.maxBatteryLevel = config.get("maxBattery", 95)
		self.hightBatteryLevel = config.get("hightBattery", 80)
		self.lowBatteryLevel = config.get("lowBattery", 20)
		self.minBatteryLevel = config.get("minBattery", 5)
		
	def switch2solarProduction(self, switch2solarProduction:bool= True):
		# TODO
		return True

	def updateNetwork(self, cycleDuration):
		batteryLevel = self.network.getBatteryLevel()
		solarProduction = self.network.getSolarProduction()
		
		if self.network.isGridSourceOn():
			if self.isDayTime():
				self.gridTime += 1
			powerConsumption = self.network.getCurrentPowerConsumption()
			if (batteryLevel>self.hightBatteryLevel) or (batteryLevel>self.lowBatteryLevel and solarProduction>powerConsumption):
				if self.switch2solarProduction():
					self.logger.info("Switched to solar production successfully.")
				else:
					self.logger.warning("Fail to switch to solar production.")
			else: # If solar production shouldn't satisfy switchable consumption, switch on devices.
				if self.itsStressyDay() and self.isOffPeakTime():
					self.switchOnMax()
				else:
					self.switchOnCriticDevices(switchOffOthers=True)
		else: # Grid source is off as it is an inverter
			if self.isDayTime():
				self.solarTime += 1
			powerConsumption = self.network.getCurrentPowerConsumption()
			# if Critic battery level
			if (batteryLevel<self.lowBatteryLevel and solarProduction<powerConsumption) or batteryLevel<self.minBatteryLevel:
				self.switchOffAll()
				if self.switch2solarProduction(False):
					self.logger.info("Switched to grid source successfully.")
				else:
					self.logger.warning("Fail to switch to grid source.")
			else: # Try to minimize battery charge/discharge cycles
				if self.switchOnCriticDevices(switchOffOthers=False):
					pass
				else:
					if solarProduction<powerConsumption-MARGIN:
						self.network.switchOff(powerConsumption-solarProduction)
					elif solarProduction>powerConsumption+MARGIN:
						self.network.switchOn(solarProduction-powerConsumption)
				
		return True

