"""
This class aim to comunicate what devices user want to schedule to the OpenHEMS core server.
The web server is the UI used to that.
"""
import logging
import datetime


class OpenHEMSSchedule:
	"""
	This class aim to comunicate what devices user want to schedule to the OpenHEMS core server.
	 The web server is the UI used to that.
	"""
	duration: int = 0
	timeout = "00:00"
	def __init__(self, haId: str, name:str, duration:int = 0, timeout:datetime = None):
		self.name = name
		self.id = haId
		self.timeout:datetime = timeout
		self.duration:int = duration
		self.logger = logging.getLogger(__name__)
		self.strategyCache = {}

	def schedule(self, timeout, duration):
		"""
		Set device duration to be on
		 AND timeout until witch all duration should be elapsed
		"""
		self.timeout = timeout
		self.duration = duration

	def isScheduled(self):
		"""
		Return True, if device is schedule to be on
		"""
		self.logger.debug("OpenHEMSSchedule.isScheduled(%s)"
			": duration = %d", self.id, self.duration)
		return self.duration>0

	def setSchedule(self, duration:int, timeout:datetime):
		"""
		Set duration for device to be on.
		"""
		msg = ("OpenHEMSSchedule.setSchedule("
			f"{duration} seconds, timeout={timeout})")
		if duration!=self.duration or self.timeout!=timeout:
			self.logger.info(msg)
		else:
			self.logger.debug(msg)
		self.duration = duration
		self.timeout = timeout
		self.strategyCache = {}

	def getStrategyCache(self, strategyId):
		"""
		Return cache used by a strategyId ()
		"""
		return self.strategyCache.get(strategyId, None)

	def setStrategyCache(self, strategyId, value):
		"""
		Set cache for a strategyId	
		"""
		self.strategyCache[strategyId] = value

	def decreaseTime(self, duration):
		"""
		decrease time to be on from elapsed time.
		"""
		self.duration = max(self.duration-duration, 0)
		return self.duration

	def __json__(self, request=None):
		"""
		Export as JSON.
		"""
		del request
		timeout = self.timeout.strftime("%H:%M") if self.timeout is not None else "0"
		return {"name":self.name,
			"duration":self.duration,
			"timeout":timeout}

	def __str__(self):
		timeout = self.timeout.strftime("%Y-%m-%d %H:%M:%S") if self.timeout is not None else "0"
		return f"Schedule({self.name}, duration:{self.duration}, timeout:{timeout})"
