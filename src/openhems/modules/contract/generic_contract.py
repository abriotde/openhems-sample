"""
Generic class to manage contracts when no more precise one is available
"""

import datetime
import logging
from openhems.modules.util.time import Time

class GenericContract:
	"""
	Generic contrat with simple offpeak-hours management
	"""
	logger = logging.getLogger(__name__)

	def __init__(self, peakPrice, offpeakPrice=None, offpeakHoursRanges=None):
		self.peakPrice = peakPrice
		if offpeakHoursRanges is None:
			offpeakHoursRanges = []
			self.offpeakPrice = peakPrice
		else:
			self.logger.info("GenericContract(offpeakHoursRanges=%s)",
				str(offpeakHoursRanges))
			self.offpeakHoursRanges = Time.getOffPeakHoursRanges(offpeakHoursRanges)
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
		offpeakHoursRanges = GenericContract.get("offpeakHoursRanges", keys)
		return (peakPrice, offpeakPrice, offpeakHoursRanges)

	def getOffPeakPrice(self):
		"""
		Return: off-peak price
		"""
		return self.offpeakHoursRanges

	def getPeakPrice(self):
		"""
		Return: peak price
		"""
		return self.peakPrice

	def getOffPeakHoursRanges(self):
		"""
		Return: off-peak hours range : list of 2-tuple of Time
		"""
		return self.offpeakPrice

	def getPrice(self, now=None):
		"""
		Return: the Kw price at 'now'.
		"""
		if self.inOffpeakRange(now):
			return self.getOffPeakPrice()
		return self.getPeakPrice()

	def inOffpeakRange(self, now=None, useCache=True):
		"""
		Return: True if we are in off-peak range.
		"""
		offpeakHoursRanges = self.getOffPeakHoursRanges()
		if len(offpeakHoursRanges)<=0:
			return False
		if not useCache or now>self.rangeEnd:
			inOffpeakRange, rangeEnd = Time.checkRange(offpeakHoursRanges, now)
			self._inOffpeakRange = inOffpeakRange
			self.rangeEnd = rangeEnd
		return self._inOffpeakRange

	@staticmethod
	def get(key, keys, defaultType=None, defaultValue=None):
		"""
		Function to get default value from configuration if not set in dict configuration
		Equivalent of HomeStateUpdater._getFeeder()
		"""
		dictConf, configuration, classname = keys
		value = dictConf.get(key, defaultType, defaultValue=defaultValue)
		if value is None:
			value = configuration.get(
				"default.node.publicpowergrid.contract."+classname+"."+key,
				defaultType
			)
		return value
