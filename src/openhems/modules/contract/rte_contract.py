"""
Module to manage RTE classic contracts. Feel automaticaly offpeak-hours and all prices
"""

import datetime
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
	def __init__(self, color, offpeakprices, peakprices, offpeakHoursRanges):
		super().__init__(offpeakprices, peakprices, offpeakHoursRanges)
		self.color = color
		self.lastCall = ""
		self.lastColor = ""

	def getColor(self, now=None):
		"""
		Return "day color". As it change every day, keep cache for 1 hour at least
		"""
		if isinstance(self.color, str):
			return self.color
		if now is None:
			now = datetime.datetime.now()
		curCall = now.strftime("%Y%m%d%H")
		if self.lastCall!=curCall:
			self.lastColor=self.color.getValue()
			self.lastCall = curCall
		return self.lastColor

	def getOffPeakPrice(self, now=None):
		color = self.getColor(now)
		price = self.offpeakPrice.get(color)
		if price is None:
			# pylint: disable=broad-exception-raised
			raise Exception(f"RTETempoContract : Invalid color : '{color}'")
		return price

	def getPeakPrice(self, now=None):
		"""
		Return peakprice 
		"""
		color = self.getColor(now)
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
		keys = (dictConf, configuration, "rtetarifbleu")
		color = GenericContract.get("color", keys, "float")
		if color is None:
			color = "bleu"
		else:
			color = networtUpdater.getFeeder(color)
			if color is None:
				color = "bleu"
		keys = (dictConf, configuration, "rtetempo")
		peakPrice = GenericContract.get("peakPrice", keys)
		offpeakPrice = GenericContract.get("offpeakPrice", keys)
		offpeakHoursRanges = GenericContract.get("offpeakHoursRanges", keys)
		return RTETempoContract(color, peakPrice, offpeakPrice, offpeakHoursRanges)

class RTEHeuresCreusesContract(RTEContract):
	"""
	Contrat RTE avec option Heures-Creuses
	"""

	@staticmethod
	def fromdict(dictConf, configuration):
		keys = (dictConf, configuration, "rteheurescreuses")
		peakPrice = GenericContract.get("peakPrice", keys, "float")
		offpeakPrice = GenericContract.get("offpeakPrice", keys, "float")
		offpeakHoursRanges = GenericContract.get("offpeakHoursRanges", keys)
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