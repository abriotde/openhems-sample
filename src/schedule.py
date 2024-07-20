
import json
from json import JSONEncoder

class OpenHEMSSchedule:
	duration: int = 0
	timeout = "00:00"
	def __init__(self, id: str, name:str, duration: int = 0, timeout = 0):
		self.name = name
		self.id = id
		self.timeout = timeout
		self.duration = duration

	def schedule(self, timeout, duration):
		self.timeout = timeout
		self.duration = duration

	def isScheduled(self):
		print("OpenHEMSSchedule.isScheduled(",self.id,") : duration = ",self.duration)
		return self.duration>0

	def setSchedule(self, duration: int, timeout):
		print("OpenHEMSSchedule.setSchedule(",duration,", ",timeout,")")
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
