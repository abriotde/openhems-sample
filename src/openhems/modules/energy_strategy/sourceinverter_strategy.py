"""
Case dual-source managed by controlled "source inverter" :
- Solar pannel and batterie managed by MPPT
- Grid
Strategy is to :
- Use grid energy when battery level is low and solar production less than consumption
- Reverse if battery level is medium and/or solar production higher
	than conumption during a certain time : batteryCapacity enought for x minutes,
	solarProductionPower>consomation from y minutes, x+y>z
Advantages : No electricity goes in grid.
Disadvantages : Could not charge battery on off-peak grid hours
 if there is not so much solar production

#TODO : Implemented - Call - Conf - TestAuto - RunOk - InProd : 0/6
"""

import logging
from openhems.modules.network.network import OpenHEMSNetwork, POWER_MARGIN
from .solarbased_strategy import SolarBasedStrategy, GeoPosition

class SourceInverterStrategy(SolarBasedStrategy):
	"""
	Case dual-source managed by controlled "source inverter" :
	- Solar pannel and batterie managed by MPPT
	- Grid
	Strategy is to :
	- Use grid energy when battery level is low and solar production less than consumption
	- Reverse if battery level is medium and/or solar production higher than conumption
	Advantages : No electricity goes in grid.
	Disadvantages : Could not charge battery on off-peak grid hours
	 if there is- not so much solar production
	"""

	def __init__(self, strategyId:str, network: OpenHEMSNetwork, geoPosition: GeoPosition, config):
		self.logger = logging.getLogger(__name__)
		self.logger.info("SourceInverterStrategy({config})")
		super().__init__(strategyId, network, geoPosition)
		self.inverterId = config.get("inverterId", "")

	def switch2solarProduction(self, switch2solarProduction:bool= True):
		"""
		Switch to solar production if switch2solarProduction=True
		Else switch to grid production, all solar production will go to battery
		"""
		del switch2solarProduction
		# TODO
		return True

	def updateNetworkUsingPublicGridSource(self, cycleDuration):
		"""
		When we use public grid source
		"""
		battery = self.network.getBattery()
		solarProduction = self.network.getSolarProduction()
		if self.isDayTime():
			self.gridTime += 1
		powerConsumption = self.network.getCurrentPower()
		if (battery.getLevel()>=battery.highLevel) \
				or (battery.getLevel()>battery.lowLevel \
				and solarProduction>powerConsumption):
			if self.switch2solarProduction():
				self.logger.info("Switched to solar production successfully.")
			else:
				self.logger.warning("Fail to switch to solar production.")
		else: # If solar production shouldn't satisfy switchable consumption, switch on devices.
			if self.itsStressyDay() and self.isOffPeakTime():
				self.switchOnMax(cycleDuration)
			else:
				self.switchOnCriticDevices(switchOffOthers=True)

	def updateNetworkUsingPrivateSource(self):
		"""
		When we use solar panel&batteries&wind private sources.
		"""
		battery = self.network.getBattery()
		solarProduction = self.network.getSolarProduction()
		if self.isDayTime():
			self.solarTime += 1
		powerConsumption = self.network.getCurrentPower()
		# if Critic battery level
		if (battery.getLevel()<battery.lowLevel \
					and solarProduction<powerConsumption\
				) or battery.getLevel()<battery.minLevel:
			self.network.switchOffAll()
			if self.switch2solarProduction(False):
				self.logger.info("Switched to grid source successfully.")
			else:
				self.logger.warning("Fail to switch to grid source.")
		else: # Try to minimize battery charge/discharge cycles
			if self.switchOnCriticDevices(switchOffOthers=False):
				pass
			else:
				if solarProduction<powerConsumption-POWER_MARGIN:
					self.network.switchOff(powerConsumption-solarProduction)
				elif solarProduction>powerConsumption+POWER_MARGIN:
					self.network.switchOn(solarProduction-powerConsumption)

	def updateNetwork(self, cycleDuration:int, now=None):
		"""
		Update the OpenHEMSNetwork
		"""
		del now
		if self.network.isGridSourceOn():
			self.updateNetworkUsingPublicGridSource(cycleDuration)
		else: # Grid source is off as it is an inverter
			self.updateNetworkUsingPrivateSource()
		return True
