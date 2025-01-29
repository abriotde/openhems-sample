"""
Generic class to manage contracts when no more precise one is available
"""

import datetime
import logging
from openhems.modules.util import HoursRanges, CastUtililty


class GenericContract:
	"""
	Generic contrat with simple offpeak-hours management
	"""
	logger = logging.getLogger(__name__)

	def __init__(self, peakPrice, offpeakPrice=None, offpeakHoursRanges=None):
		self.peakPrice = peakPrice
		if offpeakHoursRanges is None:
			self.offpeakHoursRanges = HoursRanges([])
			self.offpeakPrice = peakPrice
		else:
			self.logger.info("GenericContract(offpeakHoursRanges=%s)",
				str(offpeakHoursRanges))
			self.offpeakHoursRanges = HoursRanges(offpeakHoursRanges)
			if offpeakPrice is None:
				self.offpeakPrice = peakPrice/2
			else:
				self.offpeakPrice = offpeakPrice
		self._inOffpeakRange = None
		self.rangeEnd = datetime.datetime.now()

	@staticmethod
	def fromdict(dictConf, configuration):
		"""
		Parse a configuration dict to create a GenericContract
		"""
		peakPrice, offpeakPrice, offpeakHoursRanges = \
			GenericContract.extractFromDict(dictConf, configuration)
		return GenericContract(peakPrice, offpeakPrice, offpeakHoursRanges)

	@staticmethod
	def extractFromDict(dictConf, configuration):
		"""
		Parse a configuration dict to get key values: 
		Return tuple of (peakPrice, offpeakPrice, offpeakHoursRanges)
		"""
		keys = (dictConf, configuration, "generic")
		peakPrice = GenericContract.get("peakPrice", keys, "float")
		offpeakPrice = GenericContract.get("offpeakPrice", keys, "float")
		offpeakHoursRanges = GenericContract.get("offpeakHoursRanges", keys, "list")
		return (peakPrice, offpeakPrice, offpeakHoursRanges)

	def getOffPeakPrice(self, now=None, attime=None):
		"""
		Return: off-peak price
		"""
		del now, attime
		return self.offpeakPrice

	def getPeakPrice(self, now=None, attime=None):
		"""
		Return: peak price
		"""
		del now, attime
		return self.peakPrice

	def getOffPeakHoursRanges(self):
		"""
		Return: off-peak hours range : list of 2-tuple of Time
		"""
		return self.offpeakHoursRanges

	def getPrice(self, now=None, attime=None):
		"""
		now: datetime witch represent current time, default is datetime.now(). 
		 now must never go back further at runtime
		 now is used for cached time, usually it's datetime.now() except for test to simulate situations.
		attime: datetime witch represent time to check price. Default is now.
		Return: the Kw price at 'now'.
		"""
		if self.inOffpeakRange(now, attime):
			return self.getOffPeakPrice(now, attime)
		return self.getPeakPrice(now, attime)

	def __str__(self):
		return ("GenericContract($"
			+str(self.peakPrice)+" - "+str(self.offpeakPrice)+"/Kwh,"
			+str(self.offpeakHoursRanges)+")")

	def inOffpeakRange(self, now=None, attime=None, useCache=True):
		"""
		Return: True if we are in off-peak range.
		"""
		offpeakHoursRanges = self.getOffPeakHoursRanges()
		if offpeakHoursRanges.isEmpty():
			return False
		if not useCache or attime>self.rangeEnd:
			(inOffpeakRange, rangeEnd) = offpeakHoursRanges.checkRange(attime)
			if attime==now: # Update cache if not in a futur time
				self._inOffpeakRange = inOffpeakRange
				self.rangeEnd = rangeEnd
			else:
				return inOffpeakRange
		return self._inOffpeakRange

	@staticmethod
	def get(key, keys, defaultType=None):
		"""
		Function to get default value from configuration if not set in dict configuration
		Equivalent of HomeStateUpdater._getFeeder()
		"""
		dictConf, configuration, classname = keys
		value = dictConf.get(key)
		if value is None:
			baseKey = "default.node.publicpowergrid.contract"
			value = configuration.get(
				baseKey+"."+classname+"."+key,
				defaultType
			)
			if value is None:
				GenericContract.logger.warning(
					"No default value for '%s.%s.%s'. Availables are %s",
					baseKey, classname, key,
					configuration.get(baseKey, deepSearch=True)
				)
		elif defaultType is not None:
			value = CastUtililty.toType(defaultType, value)
		return value
