"""
This class aim to comunicate what devices user want to schedule to the OpenHEMS core server.
The web server is the UI used to that.
"""
import logging


class OpenHEMSSchedule:
	"""
	This class aim to comunicate what devices user want to schedule to the OpenHEMS core server.
	 The web server is the UI used to that.
	"""
	duration: int = 0
	timeout = "00:00"
	def __init__(self, haId: str, name:str, duration: int = 0, timeout = 0):
		self.name = name
		self.id = haId
		self.timeout = timeout
		self.duration = duration
		self.logger = logging.getLogger(__name__)

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

	def setSchedule(self, duration: int, timeout):
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
		self.timeout = timeout

	def decreaseTime(self, duration):
		"""
		decrease time to be on from elapsed time.
		"""
		self.duration = max(self.duration-duration, 0)
		return self.duration

	# pylint: disable=unused-argument
	def __json__(self, request=None):
		"""
		Export as JSON.
		"""
		return {"name":self.name,
			"duration":self.duration,
			"timeout":self.timeout}
