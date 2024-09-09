
import json
from json import JSONEncoder
import logging
logger = logging.getLogger(__name__)

class OpenHEMSSchedule:
	"""
	This class aim to comunicate what devices user want to schedule to the OpenHEMS core server. The web server is the UI used to that.
	"""
	duration: int = 0
	timeout = "00:00"
	def __init__(self, id: str, name:str, duration: int = 0, energy: int = 0, timeout = 0):
		self.name = name
		self.id = id
		self.timeout = timeout # should be a Datetime
		self.duration = duration # In seconds
		self.energy = energy # in Watt-seconds = Kwh*3_600_000
		self.logger = logging.getLogger(__name__)

	def schedule(self, timeout, duration):
		self.timeout = timeout
		self.duration = duration

	def isScheduled(self):
		self.logger.debug("OpenHEMSSchedule.isScheduled("+str(self.id)+") : duration = "+str(self.duration))
		return self.duration>0 or self.power>0

	def setSchedule(self, duration: int, timeout):
		msg = "OpenHEMSSchedule.setSchedule("+str(duration)+" seconds, timeout="+str(timeout)+")"
		if duration!=self.duration or self.timeout!=timeout:
			self.logger.info(msg)
		else:
			self.logger.debug(msg)
		self.duration = duration
		self.timeout = timeout

	def decreaseTime(self, duration, power=1):
		if power>0:
			if self.duration>0:
				self.duration -= duration
				if self.duration<=0:
					self.duration = 0
			if self.energy>0:
				self.energy -= (power*duration)
				if self.energy<=0:
					self.power = 0
		else:
			logger.warning("OpenHEMSSchedule : '"+node.id+"' power consumption is "+str(power)+" so do not deacrease time")
		return self.duration

	def __json__(self, request=None):
		return {"name":self.name, "duration":self.duration, "timeout":self.timeout}

# Useless...
class OpenHEMSJSONEncoder(JSONEncoder):
	def default(self, o):
		return o.__dict__
