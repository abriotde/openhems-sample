"""
Module to manage RTE classic contracts. Feel automaticaly offpeak-hours and all prices
"""
import time
import datetime
# import functools
import requests
from openhems.modules.network.feeder import Feeder
from openhems.modules.util import HoursRanges, ConfigurationException
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
	HOUR_DAY_CHANGE = 6
	HOUR_OFFPEAK_START = 22
	def __init__(self, color=None, colorNext=None,
	             offpeakprices=None, peakprices=None, feederProvider=None, offpeakHoursRanges=None):
		if offpeakHoursRanges is None:
			offpeakHoursRanges = [str(self.HOUR_OFFPEAK_START)+"h-"+str(self.HOUR_DAY_CHANGE)+"h"]
		if offpeakprices is None:
			offpeakprices = {"bleu":0.1, "blanc":0.2, "rouge":0.3}
		if peakprices is None:
			peakprices = {"bleu":0.4, "blanc":0.5, "rouge":0.6}
		super().__init__(offpeakHoursRanges, outRangePrice=1, defaultPrice=0)
		self.colorRanges = {}
		# self.peakprices = peakprices
		for c in peakprices.keys():
			outRangeCost=peakprices.get(c, 1)
			defaultCost=offpeakprices.get(c, 1)
			# print("RTETempoContract: HoursRanges()",defaultCost,outRangeCost,offpeakHoursRanges)
			self.colorRanges[c] = HoursRanges(
				offpeakHoursRanges, outRangeCost=outRangeCost, defaultCost=defaultCost, timeoutCallBack=self
			)
		self.historyColor = {}
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
		retVal = None
		for _ in range(3): # Could be usefull for 502 error
			self.logger.debug("Call API %s.", url)
			# User-Agent is mandatory else 502 error
			response = requests.get(url, timeout=10, allow_redirects=False,
						   headers={'User-Agent': 'Mozilla/5.0'})
			if response.status_code!=200:
				self.logger.error("Error get(%s) : %d", url, response.status_code)
				if response.status_code==502:
					self.logger.warning("Error 502: Retry in 2 seconds")
					time.sleep(2)
				else:
					return retVal
			else:
				self.logger.debug("Response: %s", response.text)
				vals = response.json()
				color = vals['codeJour']
				colorMap = {1: "bleu", 2: "blanc", 3: "rouge"}
				retVal = colorMap.get(color)
				if retVal is None:
					self.logger.error(
						"Call API url='%s' return '%s' witch is not a valid value. Values given are : %s",
						url, color, vals)
				# print(f" callApiRteTempo({day}):{retVal}")
				return retVal
		return retVal
	# callApiRteTempo("tomorrow")
	# callApiRteTempo("today")
	# callApiRteTempo("2025-03-02")

	def getColor(self, now=None, attime=None):
		"""
		Return "day color". As it change every day, keep cache for 1 hour at least
		"""
		if isinstance(self.color, str):
			# self.logger.debug("getColor() : STR(%s)", self.color)
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
		retVal = self.getHistoryColor(daytime)
		# self.logger.debug("getColor() : getHistoryColor() : %s", retVal)
		return retVal

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
		return the date in ISO format of a datetime.
		As a color date start at HOUR_DAY_CHANGE hour on morning
		  and end at HOUR_DAY_CHANGE hour the next day. 
		So a day last 24h and can be represent by a standard date 'Y-m-d'
		 but they are not corresponding.
		"""
		if int(attime.strftime("%H"))<self.HOUR_DAY_CHANGE:
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
				color = self.color.getValue()
				if color is None or not isinstance(color, str):
					self.logger.warning("RTETempoContract.getCurColor() : color is None, use the API")
					color = self.callApiRteTempo("today")
				self.lastColor = color.lower()
			else:
				self.lastColor = self.callApiRteTempo("today")
			self.lastCall = curCall
		# print("getColor() => ", self.lastColor)
		return self.lastColor

	def getHoursRanges(self, now=None, attime=None):
		"""
		Return: hours range as dedicated type
		!!! Warning : This function is not thread-safe !!!
			as one colorRange is used in multi context changing it's Limits.
		"""
		color = self.getColor(now, attime)
		hoursRanges = self.colorRanges.get(color)
		if hoursRanges is None:
			raise ConfigurationException(
				f"getHoursRanges() : RTETempoContract : Color '{color}' is not defined in configuration."
				"The configuration must specified it or the API not get this.")
		mytime = self.getTime(now, attime)
		hour = mytime.hour
		if hour<self.HOUR_DAY_CHANGE:
			timeout = mytime.replace(hour=self.HOUR_DAY_CHANGE, minute=00, second=00)
			mytime -= datetime.timedelta(hours=self.HOUR_DAY_CHANGE+1) # Go to previous day
			timeStart = mytime.replace(hour=self.HOUR_DAY_CHANGE, minute=00, second=00)
			# Warning: During 1 secons at 06:00:00, 2 hoursRange are possible,
			#  but it's less a problem than 1 second of no ranges.
		else:
			timeStart = mytime.replace(hour=self.HOUR_DAY_CHANGE, minute=00, second=00)
			mytime += datetime.timedelta(hours=25-self.HOUR_DAY_CHANGE) # Go to next day
			timeout = mytime.replace(hour=self.HOUR_DAY_CHANGE, minute=00, second=00)
		hoursRanges.setLimits(timeStart, timeout)
		return hoursRanges

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
		return RTETempoContract(color=colorFeeder, colorNext=colorNextFeeder,
		        peakprices=peakPrice, offpeakprices=offpeakPrice, offpeakHoursRanges=offpeakHoursRanges,
				feederProvider=networtUpdater)

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
		return RTEHeuresCreusesContract(
			offpeakHoursRanges, outRangePrice=peakPrice, defaultPrice=offpeakPrice
		)

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
		# pylint: disable=unexpected-keyword-arg, no-value-for-parameter
		return RTETarifBleuContract(defaultPrice=price)
