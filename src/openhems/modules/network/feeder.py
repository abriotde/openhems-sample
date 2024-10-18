
from enum import Enum
from collections import deque
from typing import Final

class Feeder:
	value = None
	def getValue(self):
		return self.value
	pass

class SourceFeeder(Feeder):
	def __init__(self, nameid, source, valueParams):
		self.nameid = nameid
		self.source = source
		if not nameid in self.source.cached_ids.keys():
			self.source.cached_ids[nameid] = [None, valueParams]
		self.source_id = 0 # For cache
	def getValue(self):
		if self.source_id<self.source.refresh_id:
			self.source_id = self.source.refresh_id # Better to update source_id before in case value is updated between this line and next one
			self.value = self.source.cached_ids[self.nameid][0]
		return self.value

class ConstFeeder(Feeder):
	def __init__(self, value, nameid=None):
		self.value = value
		if nameid is None:
			nameid = str(value)
		self.nameid = nameid


