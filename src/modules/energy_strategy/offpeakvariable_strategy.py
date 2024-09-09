from datetime import datetime, timedelta
import time
import re
import logging
from modules.network.network import OpenHEMSNetwork
from .energy_strategy import EnergyStrategy
from .offpeak_strategy import OffPeakStrategy

class OffPeakVariableStrategy(OffPeakStrategy):
	"""
	This is in case we just base on "off-peak" range hours to control output. Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours with check to not exceed authorized max consumption
	"""
	offpeakHoursRanges = []
	inOffpeakRange = False
	rangeEnd = datetime.now()
	network = None

	def __init__(self, network: OpenHEMSNetwork, offpeakHoursRanges=[["22:00:00","06:00:00"]], day):
		self.logger = logging.getLogger(__name__)
		self.logger.info("OffPeakStrategy("+str(offpeakHoursRanges)+")")
		self.network = network
		self.offpeakHoursRanges = self.parseOffPeakHoursRanges(offpeakHoursRanges)
		self.checkRange()

	def switchOnMax(self, cycleDuration):
		self.logger.info("OffPeakStrategy.switchOnMax()")
		ok = True
		done = 0
		todo = 0
		powerMargin = self.network.getMarginPowerOn()
		doSwitchOn = True
		if powerMargin<0:
			return
		for elem in self.network.out:
			if self.switchOn(elem, cycleDuration, doSwitchOn):
				doSwitchOn = False # Do just one at each loop to check Network constraint
		return todo == 0

	def updateNetwork(self, cycleDuration):
		if datetime.now()>self.rangeEnd:
			self.checkRange()
		if self.inOffpeakRange:
			# We are in off-peak range hours : switch on all
			self.switchOnMax(cycleDuration)
		else: # Sleep untill end. 
			if self.network.switchOffAll():
				self.sleepUntillNextRange()
				self.checkRange() # To update self.rangeEnd (and should change self.inOffpeakRange)
			else:
				print("Warning : Fail to swnitch off all. We will try again on next loop.")

