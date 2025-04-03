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

	def __init__(self, hoursRanges=None, defaultPrice=0.0, outRangePrice=0.15, sellPrice=0.0):
		if hoursRanges is None:
			self.hoursRanges = HoursRanges([], outRangeCost=defaultPrice)
		else:
			self.logger.info(
				"GenericContract(hoursRanges=%s, defaultCost=%s, outRangeCost=%s, sellPrice=%s)",
				str(hoursRanges), defaultPrice, outRangePrice, sellPrice)
			self.hoursRanges = HoursRanges(
				hoursRanges, defaultCost=defaultPrice , outRangeCost=outRangePrice
			)
		self._inOffpeakRange = None
		self.sellPrice = sellPrice
		self.rangeEnd = datetime.datetime.now()

	@staticmethod
	def fromdict(dictConf, configuration):
		"""
		Parse a configuration dict to create a GenericContract
		"""
		hoursRanges, defaultPrice, outRangePrice, sellPrice = \
			GenericContract.extractFromDict(dictConf, configuration)
		return GenericContract(hoursRanges, defaultPrice, outRangePrice, sellPrice=sellPrice)

	@staticmethod
	def extractFromDict(dictConf, configuration):
		"""
		Parse a configuration dict to get key values: 
		Return tuple of (peakPrice, offpeakPrice, hoursRanges)
		"""
		keys = (dictConf, configuration, "generic")
		defaultPrice = GenericContract.get("defaultPrice", keys, "float")
		outRangePrice = GenericContract.get("outRangePrice", keys, "float")
		sellPrice = GenericContract.get("sellPrice", keys, "float")
		hoursRanges = GenericContract.get("hoursRanges", keys, "list")
		return (hoursRanges, defaultPrice, outRangePrice, sellPrice)

	def getHoursRanges(self, now=None, attime=None):
		"""
		Return: hours range as dedicated type
		"""
		del now, attime
		return self.hoursRanges

	def getOffPeakHoursRanges(self, now=None, attime=None):
		"""

		Return: off-peak hours range : list of 2-tuple of Time
		"""
		peakPrice = self.getPeakPrice()
		# Filter by cost==peakPrice
		ranges = list(filter(lambda x: x[2]==peakPrice, self.getHoursRanges(now, attime)))
		return ranges

	def getPeakPrice(self, now=None, attime=None):
		"""
		:return float: the peak-price
		"""
		del now, attime
		val = max(self.getHoursRanges(now, attime).ranges, key=lambda s: (print("SSSS",s), s[2]))
		return val[2]

	def getOffPeakPrice(self, now=None, attime=None):
		"""
		:return float: the offpeak-price
		"""
		del now, attime
		val = min(self.getHoursRanges(now, attime).ranges, key=lambda s: s[2])
		return val[2]

	def getTime(self, now=None, attime=None):
		"""
		Get "attime" real value (never None)
		Consider, that if attime is None, attime=now
		And if now is None, now = datetime.datetime.now()
		"""
		if attime is None:
			attime = now
			if attime is None:
				attime = datetime.datetime.now()
		return attime


	def getPrice(self, now=None, attime=None):
		"""
		now: datetime witch represent current time, default is datetime.now(). 
		 now must never go back further at runtime
		 now is used for cached time, usually it's datetime.now() except for test to simulate situations.
		attime: datetime witch represent time to check price. Default is now.
		Return: the Kw price at 'now'.
		"""
		_, _, cost = self.getHoursRanges(now, attime).checkRange(self.getTime(now, attime))
		return cost

	def getSellPrice(self, now=None, attime=None):
		"""
		now: datetime witch represent current time, default is datetime.now(). 
		 now must never go back further at runtime
		 now is used for cached time, usually it's datetime.now() except for test to simulate situations.
		attime: datetime witch represent time to check price. Default is now.
		Return: the Kw sell cost at 'now'.
		"""
		del now, attime
		return self.sellPrice

	def __str__(self):
		return "GenericContract("+str(self.hoursRanges)+", sellPrice={self.sellPrice})"

	def inOffpeakRange(self, now=None, attime=None, useCache=True):
		"""
		Return: True if we are in off-peak range.
		"""
		hoursRanges = self.getHoursRanges()
		if hoursRanges.isEmpty():
			return False
		if not useCache or attime>self.rangeEnd:
			(inOffpeakRange, rangeEnd, _) = hoursRanges.checkRange(attime)
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
			completeKey = baseKey+"."+classname+"."+key
			value = configuration.get(
				completeKey,
				defaultType
			)
			if value is None:
				value = configuration.get(
					completeKey.lower(),
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
