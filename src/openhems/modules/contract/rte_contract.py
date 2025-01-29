"""
Module to manage RTE classic contracts. Feel automaticaly offpeak-hours and all prices
"""

import datetime
from openhems.modules.network.feeder import Feeder
from .generic_contract import GenericContract

# pylint: disable=too-few-public-methods
class RTEContract(GenericContract):
	"""
	Generic class for RTE contracts
	"""

class RTETempoContract(RTEContract):
	"""
	Contrat RTE avec option Tempo
	"""
	def __init__(self, color, colorNext,
	             offpeakprices, peakprices, offpeakHoursRanges, feederProvider):
		super().__init__(offpeakprices, peakprices, offpeakHoursRanges)
		if color is None:
			color = "Bleu"
		if not isinstance(color, Feeder):
			color = feederProvider.getFeeder(color, "str")
		self.color = color
		self.lastCall = ""
		self.lastColor = ""
		if colorNext is None:
			colorNext = "Bleu"
		if not isinstance(colorNext, Feeder):
			colorNext = feederProvider.getFeeder(colorNext)
		self.colorNext = colorNext
		self.lastCallNext = ""
		self.lastColorNext = ""

	def getColor(self, now=None, attime=None):
		"""
		Return "day color". As it change every day, keep cache for 1 hour at least
		"""
		if isinstance(self.color, str):
			return self.color
		if now==attime or attime is None:
			return self.getCurColor(now)
		if now is None:
			now = datetime.datetime.now()
		if self.areSameColorDay(now, attime):
			return self.getCurColor(now)
		return self.getNextColor(now)

	def areSameColorDay(self, now:datetime, attime:datetime):
		"""
		Check if 2 datetime	are on the same color date : 6h-22H
		Waring : Consider now<attime
		Warning : Considering that a day color start at 6 O'Clock and end at same time next day.
		"""
		if now.strftime("%Y%m%d")==attime.strftime("%Y%m%d"):
			return attime.hour<6 or now.hour>=6
		if attime.hour>=6 or now.hour<6:
			return False
		return (attime-now).total_seconds()<86400

	def getNextColor(self, now=None):
		"""
		Return the next day color according to Home-Assistant
		Warning: A beter way would be to use Web API directly
		"""
		if now is None:
			now = datetime.datetime.now()
		curCall = now.strftime("%Y%m%d%H")
		if self.lastCallNext!=curCall:
			self.lastColorNext = self.colorNext.getValue().lower()
			self.lastCallNext = curCall
		# print("getColor() => ", self.lastColor)
		return self.lastColorNext

	def getCurColor(self, now=None):
		"""
		Return the current day color according to Home-Assistant
		Warning: A beter way would be to use Web API directly
		"""
		if now is None:
			now = datetime.datetime.now()
		curCall = now.strftime("%Y%m%d%H")
		if self.lastCall!=curCall:
			self.lastColor = self.color.getValue().lower()
			self.lastCall = curCall
		# print("getColor() => ", self.lastColor)
		return self.lastColor

	def getOffPeakPrice(self, now=None, attime=None):
		print("getOffPeakPrice(:",self.color,")")
		color = self.getColor(now, attime)
		print("Color0:", color)
		price = self.offpeakPrice.get(color)
		if price is None:
			print("Color:", self.color)
			# pylint: disable=broad-exception-raised
			raise Exception(f"RTETempoContract : Invalid color : '{color}'")
		return price

	def getPeakPrice(self, now=None, attime=None):
		"""
		Return peakprice 
		"""
		color = self.getColor(now, attime)
		price = self.peakPrice.get(color)
		if price is None:
			# pylint: disable=broad-exception-raised
			raise Exception(f"RTETempoContract : Invalid color : '{color}'")
		return price

	def getOffPeakHoursRanges(self):
		return self.offpeakHoursRanges

	# pylint: disable=arguments-differ
	@staticmethod
	def fromdict(dictConf, configuration, networtUpdater):
		keys = (dictConf, configuration, "rtetempo")
		colorFeeder = GenericContract.get("color", keys)
		colorNextFeeder = GenericContract.get("nextcolor", keys)
		colors = ["bleu", "blanc", "rouge"]
		peakPrice = {}
		for c in colors:
			price = GenericContract.get("peakprice."+c, keys)
			peakPrice[c] = price
		offpeakPrice = {}
		for c in colors:
			price = GenericContract.get("offpeakprice."+c, keys)
			offpeakPrice[c] = price
		offpeakHoursRanges = GenericContract.get("offpeakhoursranges", keys, "list")
		return RTETempoContract(colorFeeder, colorNextFeeder,
		                        peakPrice, offpeakPrice, offpeakHoursRanges, networtUpdater)

class RTEHeuresCreusesContract(RTEContract):
	"""
	Contrat RTE avec option Heures-Creuses
	"""

	@staticmethod
	def fromdict(dictConf, configuration):
		keys = (dictConf, configuration, "rteheurescreuses")
		peakPrice = GenericContract.get("peakPrice", keys, "float")
		offpeakPrice = GenericContract.get("offpeakPrice", keys, "float")
		offpeakHoursRanges = GenericContract.get("offpeakHoursRanges", keys, "list")
		return RTEHeuresCreusesContract(peakPrice, offpeakPrice, offpeakHoursRanges)

class RTETarifBleuContract(RTEContract):
	"""
	Contrat RTE avec Tarif-Bleu
	"""
	def __init__(self, price):
		super().__init__(price)

	@staticmethod
	def fromdict(dictConf, configuration):
		keys = (dictConf, configuration, "rtetarifbleu")
		price = GenericContract.get("price", keys, "float")
		return RTETarifBleuContract(price)
