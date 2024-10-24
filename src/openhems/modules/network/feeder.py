"""
This Feeder aim to abstract the update of a value using the NetworkUpdater.
For the Network, we always "getValue" but when it's a dynamic value, 
the NetworkUpdater will really search to update the value. 
"""

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
