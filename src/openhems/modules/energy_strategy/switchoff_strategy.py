"""
This is in case we just base on "off-peak" range hours to control output.
	 Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours
"""

from datetime import datetime
import time
from openhems.modules.network.network import OpenHEMSNetwork
from openhems.modules.util import ConfigurationException, HoursRanges
from .energy_strategy import EnergyStrategy, LOOP_DELAY_VIRTUAL

# Time to wait in seconds before considering to be in offpeak range
TIME_MARGIN_IN_S = 1

# pylint: disable=broad-exception-raised
class SwitchOffStrategy(EnergyStrategy):
	"""
	This is in case we just base on "off-peak" range hours to control output.
	 Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours
	 with check to not exceed authorized max consumption
	"""
	offHoursRanges = []
	inOffpeakRange = False
	rangeEnd = datetime.now()
	network = None

	def __init__(self, mylogger, network: OpenHEMSNetwork, strategyId:str, 
		     offHoursRanges, reverse=False):
		super().__init__(strategyId, mylogger)
		self.network = network
		self.offHoursRanges = HoursRange(offHoursRanges)
		if reverse:
			self.offHoursRanges.getReverse()
		self.logger.info("SwitchOffStrategy(%s)", str(self.offHoursRanges))
		if not self.offHoursRanges:
			msg = "OffPeak-strategy is useless without offpeak hours. Check your configuration."
			self.logger.critical(msg)
			raise ConfigurationException(msg)
		self.checkRange()

	def checkRange(self, nowDatetime: datetime=None) -> int:
		"""
		Check if nowDatetime (Default now) is in off-peak range (offpeakHoursRange)
		 and set end time of this range
		"""
		self.inOffpeakRange, self.rangeEnd = self.offHoursRanges.checkRange(nowDatetime)

	def sleepUntillNextRange(self):
		"""
		Set application to sleep until off-peak (or inverse) range end
		TIME_MARGIN_IN_S: margin to wait more to be sure to change range... 
		useless, not scientist?
		"""
		time2wait = (self.rangeEnd - datetime.now()).total_seconds()
		self.logger.info("OffPeakStrategy.sleepUntillNextRange() : "
			"sleep(%d min, until %s)",\
			round((time2wait+TIME_MARGIN_IN_S)/60), str(self.rangeEnd))
		time.sleep(time2wait+TIME_MARGIN_IN_S)

	def switchOnAll(self, cycleDuration):
		"""
		Switch on nodes, but 
		 - If there is no margin to switch on, do nothing.
		 - Only one (To be sure to not switch on to much devices)
		"""
		self.logger.info("OffPeakStrategy.switchOnMax()")
		done = 0
		marginPower = self.network.getMarginPowerOn()
		doSwitchOn = True
		if marginPower<0:
			return True
		for elem in self.getNodes():
			if self.switchOn(elem, cycleDuration, doSwitchOn):
				# Do just one at each loop to check Network constraint
				doSwitchOn = False
				done += 1
		return done == 0

	def updateNetwork(self, cycleDuration:int, allowSleep:bool):
		"""
		Decide what to do during the cycle:
		 IF off-peak : switch on all
		 ELSE : Switch off all AND Sleep until off-peak
		"""
		if datetime.now()>self.rangeEnd:
			self.checkRange()
		if self.network.switchOffAll(self.inOffpeakRange):
			if cycleDuration>LOOP_DELAY_VIRTUAL and allowSleep:
				self.sleepUntillNextRange()
				self.checkRange() # To update self.rangeEnd (and should change self.inOffpeakRange)
		else:
			print("Warning : Fail to swnitch off all. We will try again on next loop.")
