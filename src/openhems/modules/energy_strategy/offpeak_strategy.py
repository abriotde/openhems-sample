"""
This is in case we just base on "off-peak" range hours to control output.
	 Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours
"""

from datetime import datetime
from openhems.modules.network.network import OpenHEMSNetwork
from openhems.modules.util import ConfigurationException
from .energy_strategy import EnergyStrategy, LOOP_DELAY_VIRTUAL


# pylint: disable=broad-exception-raised
class OffPeakStrategy(EnergyStrategy):
	"""
	This is in case we just base on "off-peak" range hours to control output.
	 Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours
	 with check to not exceed authorized max consumption
	"""

	def __init__(self, mylogger, network: OpenHEMSNetwork, strategyId:str):
		super().__init__(strategyId, network, mylogger)
		self.inOffpeakRange = False
		self.rangeEnd = datetime.now()
		self.offpeakHoursRanges = self.network.getOffPeakHoursRanges()
		self.logger.info("OffPeakStrategy(%s) on %s", str(self.offpeakHoursRanges), str(self.getNodes()))
		if not self.offpeakHoursRanges:
			msg = "OffPeak-strategy is useless without offpeak hours. Check your configuration."
			self.logger.critical(msg)
			raise ConfigurationException(msg)
		self._rangeChangeDone = False
		self.checkRange()

	def checkRange(self, nowDatetime: datetime=None) -> int:
		"""
		Check if nowDatetime (Default now) is in off-peak range (offpeakHoursRange)
		 and set end time of this range
		"""
		self.offpeakHoursRanges = self.network.getOffPeakHoursRanges()
		inoffpeak = self.inOffpeakRange
		self.inOffpeakRange, self.rangeEnd = self.offpeakHoursRanges.checkRange(nowDatetime)
		if inoffpeak!=self.inOffpeakRange:
			self._rangeChangeDone = False

	def switchOnMax(self, cycleDuration):
		"""
		Switch on nodes, but 
		 - If there is no margin to switch on, do nothing.
		 - Only one (To be sure to not switch on to much devices)
		"""
		self.logger.info("%s.switchOnMax()", self.strategyId)
		done = 0
		marginPower = self.network.getMarginPowerOn()
		doSwitchOn = True
		if marginPower<0:
			self.logger.info("Can't switch on devices: not enough power margin : %s", marginPower)
			return True
		for elem in self.getNodes():
			if self.switchOnSchedulable(elem, cycleDuration, doSwitchOn):
				# Do just one at each loop to check Network constraint
				doSwitchOn = False
				done += 1
		return done == 0

	def updateNetwork(self, cycleDuration:int, allowSleep:bool, now=None) -> int:
		"""
		Decide what to do during the cycle:
		 IF off-peak : switch on all
		 ELSE : Switch off all AND Sleep until off-peak
		"""
		if now is None:
			now = datetime.now()
		if now>self.rangeEnd:
			self.checkRange()
		if self.inOffpeakRange:
			# We are in off-peak range hours : switch on all
			self.switchOnMax(cycleDuration)
		else: # Sleep untill end.
			if not self._rangeChangeDone:
				self.logger.debug("OffpeakStrategy : not offpeak, switchOffAll()")
				if self.switchOffAll():
					if cycleDuration>LOOP_DELAY_VIRTUAL and allowSleep:
						self.offpeakHoursRanges.sleepUntillNextRange(now)
						self.checkRange() # To update self.rangeEnd (and should change self.inOffpeakRange)
					else:
						self._rangeChangeDone = True
						return self.offpeakHoursRanges.getTime2NextRange(now)
				else:
					self.logger.warning("Fail to switch off all. We will try again on next loop.")
		return 0
