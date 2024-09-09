import astral, datetime
from .offpeak_strategy import OffPeakStrategy
from modules.network.network import OpenHEMSNetwork



class SolarBasedStrategy(OffPeakVariableStrategy):
	"""
		Abstract class for photovoltaic based production
	"""
	def  __init__(self, network: OpenHEMSNetwork, latitude, longitude, offpeakHoursRanges=[["17:00:00","09:00:00"]]):
		self._nightime = False
		self.isDayTime()
		self.timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
		self.location = astral.LocationInfo('Custom Name', 'My Region', str(self.timezone), latitude, longitude)
		self.gridTime = 0
		self.solarTime = 0
		self.lastAutonomousRatio = 0
		self.setOffPeakHoursRanges(offpeakHoursRanges)
		self.checkRange()

	def updateNetwork(self):
		logging.getLogger("SolarBasedStrategy").error("SolarBasedStrategy.updateNetwork() : To implement in sub-class")

	def getAutonomousRatio(self):
		return 100 * self.solarTime / (self.solarTime+self.gridTime) if (self.solarTime+self.gridTime)>0 else 0

	def isDayTime(self):
		"""
			Return True if it's daytime, else return false if it's nighttime
			usefull for solar production management
		"""
		now = datetime.now()
		if self._nightime:
			if now>self._sunrise:
				self._nightime = False
		else:
			if now>self._sunset:
				self._nightime = True
				tomorow_date = datetime.date.today() + datetime.timedelta(days=1)
				sun = astral.sun.sun(self.location.observer, date=tomorow_date)
				self._sunrise = sun['sunrise'].astimezone(self.timezone)
				self._nightime = sun['sunset'].astimezone(self.timezone)
				self.lastAutonomousRatio = self.getAutonomousRatio()
				self.solarTime = self.gridTime = 0

	def itsStressyDay(self):
		return self.lastAutonomousRatio<50 and self.getAutonomousRatio()<50

	def switchOnCriticDevices(self, switchOffOthers:bool=False):
		"""
		Switch on devices witch must start now  to finish on time.
		If switchOffOthers is true, it will switch off others devices on
		"""
		# TODO

	def isOffPeakTime(self):
		"""
		@return: True if we are in off-peak time. If there is none off-peak's return true (Like we are always on off-peak time, so we  can use electricity all the time as we want nethermind.)
		"""
		if len(self.offpeakHoursRanges)<=0:
			return True
		if datetime.now()>self.rangeEnd:
			self.checkRange()
		return self.inOffpeakRange

