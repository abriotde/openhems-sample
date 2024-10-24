"""
This is in case we just base on "off-peak" range hours to control output.
	 Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours
"""

from datetime import datetime
import time
import re
import logging
from openhems.modules.network.network import OpenHEMSNetwork
from .energy_strategy import EnergyStrategy

# Time to wait in seconds before considering to be in offpeak range
TIME_MARGIN_IN_S = 1

# pylint: disable=broad-exception-raised
class OffPeakStrategy(EnergyStrategy):
	"""
	This is in case we just base on "off-peak" range hours to control output.
	 Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours
	 with check to not exceed authorized max consumption
	"""
	offpeakHoursRanges = []
	inOffpeakRange = False
	rangeEnd = datetime.now()
	network = None

	def __init__(self, network: OpenHEMSNetwork, offpeakHoursRanges=None):
		self.logger = logging.getLogger(__name__)
		if offpeakHoursRanges is None:
			offpeakHoursRanges = [["22:00:00","06:00:00"]]
		self.logger.info("OffPeakStrategy({offpeakHoursRanges})")
		self.network = network
		self.setOffPeakHoursRanges(offpeakHoursRanges)
		self.checkRange()

	@staticmethod
	def getTime(strTime:str):
		"""
		Convert different time configuration as srting to custom Mytime : "%H%M%S"
		"""
		strTime = strTime.strip()
		if not re.match("^[0-9]+:[0-9]+:[0-9]+$", strTime) is None:
			pattern = '%H:%M:%S'
		elif not re.match("^[0-9]+:[0-9]+$", strTime) is None:
			pattern = '%H:%M'
		elif not re.match("^[0-9]+h?$", strTime) is None:
			pattern = '%Hh'
		elif not re.match("^[0-9]+h?[0-9]+$", strTime) is None:
			pattern = '%Hh%M'
		else:
			raise Exception("Fail convert '{strTime}' to Time.")
		return int(datetime.strptime(strTime, pattern).strftime("%H%M%S"))

	def setOffPeakHoursRanges(self, offPeakHoursRanges):
		"""
		Convert the configuration array of offpeakHoursRanges
		 to a usable array of 'object'.
		"""
		self.offpeakHoursRanges = []
		for offpeakHoursRange in offPeakHoursRanges:
			begin = self.getTime(offpeakHoursRange[0])
			end = self.getTime(offpeakHoursRange[1])
			self.offpeakHoursRanges.append([begin, end])

	def checkRange(self, nowDatetime: datetime=None) -> int:
		"""
		Check if nowDatetime (Default now) is in off-peak range (offpeakHoursRange)
		 and set end time of this range
		"""
		if nowDatetime is None:
			nowDatetime = datetime.now()
		now = self.datetime2Mytime(nowDatetime)
		# print("OffPeakStrategy.checkRange(",now,")")
		self.inOffpeakRange = False
		nextTime = now+EnergyStrategy.MIDNIGHT
		# This has no real signification but it's usefull and the most simple way
		time2NextTime = EnergyStrategy.MIDNIGHT
		for offpeakHoursRange in self.offpeakHoursRanges:
			begin, end = offpeakHoursRange
			wait = self.getTimeToWait(now, begin)
			if wait<time2NextTime:
				nextTime = begin
				time2NextTime = wait
				self.inOffpeakRange = False
			wait = self.getTimeToWait(now, end)
			if wait<time2NextTime:
				nextTime = end
				time2NextTime = wait
				self.inOffpeakRange = True
		assert nextTime<=240000
		self.rangeEnd = self.mytime2datetime(nowDatetime, nextTime)
		nbSecondsToNextRange = (self.rangeEnd - nowDatetime).total_seconds()
		self.logger.info("OffPeakStrategy.checkRange({now}) => {self.rangeEnd}, {nbSecondsToNextRange}")
		return nbSecondsToNextRange

	def sleepUntillNextRange(self):
		"""
		Set application to sleep until off-peak (or inverse) range end
		MARGIN: margin to wait more to be sure to change range... 
		useless, not scientist?
		"""
		time2wait = (self.rangeEnd - datetime.now()).total_seconds()
		self.logger.info("OffPeakStrategy.sleepUntillNextRange() :\
			sleep({round((time2wait+MARGIN)/60)} min, until {self.rangeEnd})")
		time.sleep(time2wait+TIME_MARGIN_IN_S)


	def switchOn(self, node, cycleDuration, doSwitchOn=True):
		"""
		IF the node is ever on:
		 - decrement his time to be on from cycleDuration
		 - Switch off the node if time to be on elapsed
		ELSE IF doSwitchOn=True: Switch on the node
		"""
		if node.isSwitchable:
			if node.isOn():
				lastDuration = node.getSchedule().decreaseTime(cycleDuration)
				self.logger.debug("Node {node.id} isOn for {lastDuration} more seconds")
				if lastDuration==0:
					self.logger.info("Switch off {node.id} due to elapsed time.")
					if node.switchOn(False):
						self.logger.warning("Fail switch off {node.id}.")
			elif doSwitchOn and node.getSchedule().isScheduled():
				if node.switchOn(True):
					self.logger.info("Switch on '{node.id}' successfully.")
					return True
				self.logger.warning("Fail switch on {node.id}.")
			else:
				self.logger.debug("switchOn() : Node is off and not schedule : {node.id}.")
		else:
			self.logger.debug("switchOn() : Node is not switchable : {node.id}.")
		return False

	def switchOnMax(self, cycleDuration):
		"""
		Switch on nodes, but 
		 - If there is no margin to switch on, do nothing.
		 - Only one (To be sure to not switch on to much devices)
		"""
		self.logger.info("OffPeakStrategy.switchOnMax()")
		done = 0
		powerMargin = self.network.getMarginPowerOn()
		doSwitchOn = True
		if powerMargin<0:
			return True
		for elem in self.network.out:
			if self.switchOn(elem, cycleDuration, doSwitchOn):
				# Do just one at each loop to check Network constraint
				doSwitchOn = False
				done += 1
		return done == 0

	def updateNetwork(self, cycleDuration):
		"""
		Decide what to do during the cycle:
		 IF off-peak : switch on all
		 ELSE : Switch off all AND Sleep until off-peak
		"""
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
