"""
Super class for all solar-based strategy
"""

import datetime
from dataclasses import dataclass
import astral
from astral.sun import sun
from openhems.modules.network.network import OpenHEMSNetwork
from openhems.modules.util import ConfigurationManager
from .energy_strategy import EnergyStrategy

@dataclass
class GeoPosition:
	"""
	Class to represent Geographical position 
	"""
	lat:float
	lon:float
	alt:float

	def getLatLon(self):
		"""
		Return array of latitude/longitude. 
		"""
		return [self.lat, self.lon]

class SolarBasedStrategy(EnergyStrategy):
	"""
	Super class for all solar-based strategy
	:param strategyId: A string as nameid
	:param network: An OpenHEMSNetwork representing the home electricity network
	:param configurationGlobal: An ConfigurationManager representing the wall application configuration
	"""
	def  __init__(self, strategyId, network:OpenHEMSNetwork,
			configurationGlobal:ConfigurationManager , myLogger=None):
		super().__init__(strategyId, network, myLogger)
		self.geoposition = GeoPosition(
			configurationGlobal.get("localization.latitude"),
			configurationGlobal.get("localization.longitude"),
			configurationGlobal.get("localization.altitude")
		)
		self._nightime = False
		self._sunrise = datetime.datetime.now() # TODO
		self._sunset = datetime.datetime.now() # TODO
		self.timezone = datetime.datetime.now(datetime.timezone.utc)\
			.astimezone().tzinfo
		self.location = astral\
			.LocationInfo('Custom Name', 'My Region', \
				str(self.timezone), self.geoposition.lat, self.geoposition.lon)
		self.gridTime = 0
		self.solarTime = 0
		self.lastAutonomousRatio = 0
		# Init self._sunset && self.location before calling isDayTime()
		self.isDayTime()

	# def updateNetwork(self, cycleDuration:int, now=None):
	# 	"""
	# 	Update the OpenHEMSNetwork.
	# 	"""
	# 	return super().updateNetwork(cycleDuration, now)

	def getAutonomousRatio(self):
		"""
		Get a ratio of autonomy from last 24h.
		"""
		if (self.solarTime+self.gridTime)>0:
			return 100 * self.solarTime / (self.solarTime+self.gridTime)
		return 0

	def isDayTime(self, now=None):
		"""
		Return True if it's daytime, else return false if it's nighttime
		usefull for solar production management
		"""
		if now is None:
			now = datetime.datetime.now()
		if self._nightime:
			if now>self._sunrise:
				self._nightime = False
		else:
			if now>self._sunset:
				self._nightime = True
				tomorowDate = datetime.date.today() + datetime.timedelta(days=1)
				sunParams = sun(self.location.observer, date=tomorowDate)
				self._sunrise = sunParams['sunrise'].astimezone(self.timezone)
				self._nightime = sunParams['sunset'].astimezone(self.timezone)
				self.lastAutonomousRatio = self.getAutonomousRatio()
				self.solarTime = self.gridTime = 0

	def itsStressyDay(self):
		"""
		Return true if we should lack energy today
		"""
		return self.lastAutonomousRatio<50 and self.getAutonomousRatio()<50

	def switchOnCriticDevices(self, switchOffOthers:bool=False):
		"""
		Switch on devices witch must start now  to finish on time.
		If switchOffOthers is true, it will switch off others devices on
		"""
		# TODO

	def isOffPeakTime(self):
		"""
		@return: True if we are in off-peak time. 
		If there is none off-peak's return true 
		(Like we are always on off-peak time, so we  can use electricity
		 all the time as we want nethermind.)
		"""
		hoursRange = self.network.getHoursRanges()
		inOffpeakRange, _, _ = hoursRange.checkRange()
		return inOffpeakRange
