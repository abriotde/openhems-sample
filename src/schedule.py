
import json
from json import JSONEncoder

class OpenHEMSSchedule:
	def __init__(self, id: str, name:str, duration = 0, timeout = 0):
		self.name = name
		self.id = id
		self.timeout = timeout
		self.duration = duration

	def schedule(self, timeout, duration):
		self.timeout = timeout
		self.duration = duration

	def __json__(self, request=None):
		return {"name":self.name, "duration":self.duration, "timeout":self.timeout}

# Useless...
class OpenHEMSJSONEncoder(JSONEncoder):
	def default(self, o):
		return o.__dict__