"""
This Feeder aim to abstract the update of a value using the NetworkUpdater.
For the Network, we always "getValue" but when it's a dynamic value, 
the NetworkUpdater will really search to update the value. 
"""

import random

# pylint: disable=too-few-public-methods
class Feeder:
	"""
	Abstract class to reprensent the concept:
	This Feeder aim to abstract the update of a value using the NetworkUpdater.
	For the Network, we always "getValue" but when it's a dynamic value, 
	the NetworkUpdater will really search to update the value.
	For exemple : The maximum power we can give can be constant (From the grid)
	 or variable like form battery/solar-panel.
	But sometime, it's just because we do not have a sensor for this, 
	so we use const value as "patch".
	"""
	def __init__(self, value=None):
		self.value = value
	def getValue(self):
		"""
		Return Value. Ths is default implementation
		"""
		return self.value

# pylint: disable=too-few-public-methods
class SourceFeeder(Feeder):
	"""
	Get value from Network.
	"""
	def __init__(self, nameid, source, valueParams):
		super().__init__()
		self.nameid = nameid
		self.source = source
		if not nameid in self.source.cached_ids.keys():
			self.source.cached_ids[nameid] = [None, valueParams]
		self.source_id = 0 # For cache
	def getValue(self):
		"""
		getValue from the "source" if source.id has been updated.
		"""
		if self.source_id<self.source.refresh_id:
			# Better to update source_id before in case value is
			# updated between the 2 next lines
			self.source_id = self.source.refresh_id
			self.value = self.source.cached_ids[self.nameid][0]
		return self.value

# pylint: disable=too-few-public-methods
class ConstFeeder(Feeder):
	"""
	This is for value wich are constant.
	"""
	def __init__(self, value, nameid=None):
		super().__init__(value)
		if nameid is None:
			nameid = str(value)
		self.nameid = nameid

class RandomFeeder(Feeder):
	"""
	The return 'value' is a random value between a 'minimum' and 'maximum',
	 but on each openHEMS cycles it does not change a lot usualy.
	The evolution is quite slow witch is more realistic.
	"""
	def __init__(self, source, minimum, maximum, averageStep=None):
		self.source = source
		self.min = minimum
		self.max = maximum
		if averageStep is None:
			averageStep = (maximum - minimum)/10
		self.avgStep = averageStep
		self.value = (minimum + maximum) / 2
		self.last_refresh_id = self.source.refresh_id-1

	def getValue(self):
		"""
		The return 'value' is a random value between a 'minimum' and 'maximum',
		But each step is a gaussian step between the current value.
		"""
		if self.last_refresh_id < self.source.refresh_id:
			self.value = min(max(
					self.value + random.gauss(0, 2*self.avgStep),
				self.min), self.max)
		return self.value

class RotationFeeder(Feeder):
	"""
	The return 'value' rotate on a list of predefined 'values'.
	It can be usefull to simulate a cylcle or random but with predicaled values
	 (Usefull for tests)
	"""
	def __init__(self, source, valuesList:list):
		self.values = valuesList
		self.len = len(valuesList)
		self.source = source

	def getValue(self):
		"""
		The return 'value' rotate on a list of predefined 'values'.
		On each OpenHEMS server loop, self.source.refresh_id should increment,
		 witch occure the change, 
		"""
		i = self.source.refresh_id % self.len
		return self.values[i]
