"""
This Feeder aim to abstract the update of a value using the NetworkUpdater.
For the Network, we always "getValue" but when it's a dynamic value, 
the NetworkUpdater will really search to update the value. 
"""

import random
import logging
from openhems.modules.util import CastUtililty

logger = logging.getLogger(__name__)

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
		if not nameid in self.source.cachedIds.keys():
			self.source.cachedIds[nameid] = [None, valueParams]
		self.sourceId = 0 # For cache
	def getValue(self):
		"""
		getValue from the "source" if source.id has been updated.
		"""
		if self.source.refreshId==0:
			logger.warning("SourceFeeder() : Need to refresh Network...")
			self.source.updateNetwork()
		if self.sourceId<self.source.refreshId:
			# Better to update sourceId before in case value is
			# updated between the 2 next lines
			self.sourceId = self.source.refreshId
			self.value = self.source.cachedIds[self.nameid][0]
		return self.value
	def __str__(self):
		return "SourceFeeder("+self.nameid+")"

# pylint: disable=too-few-public-methods
class ConstFeeder(Feeder):
	"""
	This is for value wich are constant.
	"""
	def __init__(self, value, nameid=None, expectedType=None):
		if expectedType is not None:
			value = CastUtililty.toType(expectedType, value)
		super().__init__(value)
		if nameid is None:
			nameid = str(value)
		self.nameid = nameid
	def __str__(self):
		return "'"+self.nameid+"'"

class RandomFeeder(Feeder):
	"""
	The return 'value' is a random value between a 'minimum' and 'maximum',
	 but on each openHEMS cycles it does not change a lot usualy.
	The evolution is quite slow witch is more realistic.
	"""
	def __init__(self, source, minimum, maximum, averageStep=None):
		super().__init__((minimum + maximum) / 2)
		self.source = source
		self.min = minimum
		self.max = maximum
		if averageStep is None:
			averageStep = (maximum - minimum)/10
		self.avgStep = averageStep
		self.lastRefreshId = self.source.refreshId-1

	def getValue(self):
		"""
		The return 'value' is a random value between a 'minimum' and 'maximum',
		But each step is a gaussian step between the current value.
		"""
		if self.lastRefreshId < self.source.refreshId:
			self.value = min(max(
					self.value + random.gauss(0, 2*self.avgStep),
				self.min), self.max)
		return self.value
	def __str__(self):
		return "RandomFeeder("+str(self.min)+", "+str(self.max)+")"

class RotationFeeder(Feeder):
	"""
	The return 'value' rotate on a list of predefined 'values'.
	It can be usefull to simulate a cylcle or random but with predicaled values
	 (Usefull for tests)
	"""
	def __init__(self, source, valuesList:list):
		self.len = len(valuesList)
		if self.len==0:
			logger.error("RotationFeeder() init with empty list. Sert to default [0]")
			valuesList = [0]
			self.len = len(valuesList)
		super().__init__(valuesList[0])
		self.values = valuesList
		self.source = source

	def getValue(self):
		"""
		The return 'value' rotate on a list of predefined 'values'.
		On each OpenHEMS server loop, self.source.refreshId should increment,
		 witch occure the change, 
		"""
		i = self.source.refreshId % self.len
		return self.values[i]
	def __str__(self):
		return "RotationFeeder("+str(self.values)+")"

class StateFeeder(ConstFeeder):
	"""
	This is a state machine : This value is the one set before.
	(Like a ConstFeeder that we can change)
	"""

	def setValue(self, value):
		"""
		Change the value to new one.
		"""
		self.value = value
	def __str__(self):
		return "StateFeeder("+str(self.value)+")"

class FakeSwitchFeeder(Feeder):
	"""
	The return 'value' rotate on a list of predefined 'values'.
	It can be usefull to simulate a cylcle or random but with predicaled values
	 (Usefull for tests)
	"""
	def __init__(self, source:Feeder, isOn:Feeder, defaultValue=0):
		super().__init__(source)
		self.isOn = isOn
		self.defaultValue = defaultValue

	def getValue(self):
		"""
		The return 'value' rotate on a list of predefined 'values'.
		On each OpenHEMS server loop, self.source.refreshId should increment,
		 witch occure the change, 
		"""
		if self.isOn.getValue():
			return self.value.getValue()
		return self.defaultValue
	def __str__(self):
		return "FakeSwitchFeeder()"
