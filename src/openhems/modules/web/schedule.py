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
	def __init__(self, haId: str, name:str, timeout=None,
			duration:int=0, energy:int=0, cycleId=None):
		self.logger = logging.getLogger(__name__)
		self.name = name
		self.id = haId
		if timeout is None:
			timeout = datetime.datetime.now() + datetime.timedelta(days=5)
		self.timeout = timeout
		self.duration: int = duration # in seconds
		self.energy: float = energy # in Wh
		self.cycleId = cycleId

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
		return self.duration>0 or self.kwh>0 or self.cycleId is not None

	def setSchedule(self, *, duration:int=0, energy:int=0, cycleId=None, timeout=None):
		"""
		Set duration for device to be on.
		"""
		msg = ("OpenHEMSSchedule.setSchedule("
			"{duration} seconds, timeout={timeout})")
		if duration!=self.duration or self.timeout!=timeout:
			self.logger.info(msg)
		else:
			self.logger.debug(msg)
		self.duration = duration
		self.energy = energy
		self.timeout = timeout

	def decreaseTime(self, duration, power):
		"""
		decrease time to be on from elapsed time.
		@return : True if there is more scheduled to do.
		"""
		self.duration = self.duration-duration
		energy = power*duration/3600 # watt * heure = watt * seconds/3600
		self.energy = self.energy-energy
		return self.isScheduled()

	# pylint: disable=unused-argument
	def __json__(self, request=None):
		"""
		Export as JSON.
		"""
		return {"name":self.name,
			"duration":self.duration,
			"timeout":self.timeout}
