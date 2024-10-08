
import json
from json import JSONEncoder
import logging


class OpenHEMSSchedule:
	"""
	This class aim to comunicate what devices user want to schedule to the OpenHEMS core server. The web server is the UI used to that.
	"""
	duration: int = 0
	timeout = "00:00"
	def __init__(self, id: str, name:str, duration: int = 0, timeout = 0):
		self.name = name
		self.id = id
		self.timeout = timeout
		self.duration = duration
		self.logger = logging.getLogger(__name__)

	def schedule(self, timeout, duration):
		self.timeout = timeout
		self.duration = duration

	def isScheduled(self):
		self.logger.debug("OpenHEMSSchedule.isScheduled("+str(self.id)+") : duration = "+str(self.duration))
		return self.duration>0

	def setSchedule(self, duration: int, timeout):
		msg = "OpenHEMSSchedule.setSchedule("+str(duration)+" seconds, timeout="+str(timeout)+")"
		if duration!=self.duration or self.timeout!=timeout:
			self.logger.info(msg)
		else:
			self.logger.debug(msg)
		self.duration = duration
		self.timeout = timeout

	def decreaseTime(self, duration):
		self.duration -= duration
		if self.duration<0:
			self.duration = 0
		return self.duration

	def __json__(self, request=None):
		return {"name":self.name, "duration":self.duration, "timeout":self.timeout}

# Useless...
class OpenHEMSJSONEncoder(JSONEncoder):
	def default(self, o):
		return o.__dict__
