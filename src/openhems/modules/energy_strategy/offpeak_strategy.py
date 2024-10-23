from datetime import datetime, timedelta
import time
import re
import logging
from openhems.modules.network.network import OpenHEMSNetwork
from .energy_strategy import EnergyStrategy

class OffPeakStrategy(EnergyStrategy):
	"""
	This is in case we just base on "off-peak" range hours to control output. Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours with check to not exceed authorized max consumption
	"""
	offpeakHoursRanges = []
	inOffpeakRange = False
	rangeEnd = datetime.now()
	network = None

	def __init__(self, network: OpenHEMSNetwork, offpeakHoursRanges=[["22:00:00","06:00:00"]]):
		self.logger = logging.getLogger(__name__)
		self.logger.info("OffPeakStrategy("+str(offpeakHoursRanges)+")")
		self.network = network
		self.setOffPeakHoursRanges(offpeakHoursRanges)
		self.checkRange()

	@staticmethod
	def getTime(strTime:str):
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
			raise Exception("Fail convert '%s' to Time." % strTime)
		return int(datetime.strptime(strTime, pattern).strftime("%H%M%S"))

	def setOffPeakHoursRanges(self, offPeakHoursRanges):
		self.offpeakHoursRanges = []
		for offpeakHoursRange in offPeakHoursRanges:
			begin = self.getTime(offpeakHoursRange[0])
			end = self.getTime(offpeakHoursRange[1])
			self.offpeakHoursRanges.append([begin, end])

	
	def checkRange(self, nowDatetime: datetime=None) -> int:
		if nowDatetime is None:
			nowDatetime = datetime.now()
		now = self.datetime2Mytime(nowDatetime)
		# print("OffPeakStrategy.checkRange(",now,")")
		self.inOffpeakRange = False
		nextTime = now+EnergyStrategy.MIDNIGHT
		time2NextTime = EnergyStrategy.MIDNIGHT # This has no real signification but it's usefull and the most simple way
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
		self.logger.info("OffPeakStrategy.checkRange("+str(now)+") => "+str(self.rangeEnd)+ ", "+str(nbSecondsToNextRange))
		return nbSecondsToNextRange

	def sleepUntillNextRange(self):
		MARGIN = 1 # margin to wait more to be sure to change range... useless, not scientist?
		time2wait = (self.rangeEnd - datetime.now()).total_seconds()
		self.logger.info("OffPeakStrategy.sleepUntillNextRange() : sleep("+str(round((time2wait+MARGIN)/60))+" min, until "+str(self.rangeEnd)+")")
		time.sleep(time2wait+MARGIN)


	def switchOn(self, node, cycleDuration, doSwitchOn=True):
		if node.isSwitchable:
			if node.isOn():
				lastDuration = node.getSchedule().decreaseTime(cycleDuration)
				self.logger.debug("Node "+node.id+" isOn for "+str(lastDuration)+" more seconds")
				if lastDuration==0:
					self.logger.info("Switch off "+node.id+" due to elapsed time.")
					if node.switchOn(False):
						self.logger.warning("Fail switch off "+node.id+".")
			elif doSwitchOn and node.getSchedule().isScheduled():
				if node.switchOn(True):
					self.logger.info("Switch on '"+str(node.id)+"' successfully.")
					return True
				else:
					self.logger.warning("Fail switch on "+node.id+".")
			else:
				self.logger.debug("switchOn() : Node is off and not schedule : "+node.id+".")
		else:
			self.logger.debug("switchOn() : Node is not switchable : "+node.id+".")
		return False

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

