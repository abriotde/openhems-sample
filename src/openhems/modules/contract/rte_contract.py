"""
Module to manage RTE classic contracts. Feel automaticaly offpeak-hours and all prices
"""

import datetime
# import functools
import requests
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
	             offpeakprices, peakprices, offpeakHoursRanges, feederProvider=None):
		super().__init__(offpeakprices, peakprices, offpeakHoursRanges)
		if color is not None and not isinstance(color, Feeder):
			color = feederProvider.getFeeder(color, "str")
		self.color = color
		self.lastCall = ""
		self.lastColor = ""
		if colorNext is not None and not isinstance(colorNext, Feeder):
			colorNext = feederProvider.getFeeder(colorNext)
		self.colorNext = colorNext
		self.lastCallNext = ""
		self.lastColorNext = ""

	# idClient = "4c8e84ae-4c0a-4f00-838a-66ca6bc3a7b4"
	# idSecret = "f1a76990-3e0c-4b03-bc5e-87f94afdb956"
	# url = "https://digital.iservices.rte-france.com/open_api/tempo_like_supply_contract/v1"
	# https://www.api-couleur-tempo.fr/api
	def callApiRteTempo(self, day):
		"""
			Use https://www.api-couleur-tempo.fr/api/ API to get TempoColori of a day.
		"""
		url = "https://www.api-couleur-tempo.fr/api/jourTempo/"+day
		response = requests.get(url, timeout=10)
		if response.status_code!=200:
			print("Error get(%s)", url)
			retVal = None
		else:
			vals = response.json()
			color = vals['codeJour']
			colorMap = {1: "bleu", 2: "blanc", 3: "rouge"}
			retVal = colorMap.get(color)
		# print(f" callApiRteTempo({day}):{retVal}")
		return retVal
	# callApiRteTempo("tomorrow")
	# callApiRteTempo("today")
	# callApiRteTempo("2025-03-02")

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
		daytime = self.getColorDate(attime)
		if self.getColorDate(now)==daytime:
			return self.getCurColor(now)
		if attime>now:
			return self.getNextColor(now)
		return self.getHistoryColor(daytime)

	# @functools.cache
	def getHistoryColor(self, attime):
		"""
		Return the color of a passed date.
		"""
		if not isinstance(attime, str):
			day = self.getColorDate(attime)
		else:
			day = attime
		return self.callApiRteTempo(day)

	def getColorDate(self, attime):
		"""
		As a color date start at 6 hour on morning and end at 6 hour the next day. 
		So a day last 24h and can be represent by a standard date 'Y-m-d'
		 but they are not corresponding.
		"""
		if int(attime.strftime("%H"))<6:
			attime = attime-datetime.timedelta(days=1)
		return attime.strftime("%Y-%m-%d")

	def getNextColor(self, now=None):
		"""
		Return the next day color according to Home-Assistant
		Warning: A beter way would be to use Web API directly
		"""
		if now is None:
			now = datetime.datetime.now()
		curCall = now.strftime("%Y%m%d%H")
		if self.lastCallNext!=curCall:
			if self.colorNext is not None:
				self.lastColorNext = self.colorNext.getValue().lower()
			else:
				self.lastColorNext = self.callApiRteTempo("tomorrow")
			# TODO : check lastColorlNext is coherent
			self.lastCallNext = curCall
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
			if self.color is not None:
				self.lastColor = self.color.getValue().lower()
			else:
				self.lastColor = self.callApiRteTempo("today")
			# TODO : check value
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
