from datetime import datetime, timedelta
import time
import re
import logging
from modules.network.network import OpenHEMSNetwork

class OffPeakManager:
	MIDNIGHT = 240000

	def __init__(self, offpeakHoursRanges=[["22:00:00","06:00:00"]]):
		self.offpeakHoursRanges = self.offpeakHoursRanges
		self.offpeakHoursRanges = self.parseOffPeakHoursRanges(offpeakHoursRanges)
		self.inOffpeakRange, self.rangeEnd = self.checkRange()
	
	@staticmethod
	def datetime2Mytime(time: datetime):
		return int(time.strftime("%H%M%S"))
	@staticmethod
	def mytime2hourMinSec(time):
		secs = time%100
		min = int(time/100)%100
		hours = int(time/10000)
		return  [hours, min, secs]
	@staticmethod
	def mytime2datetime(now: datetime, time):
		nowtime = EnergyStrategy.datetime2Mytime(now)
		h0, m0, s0 = EnergyStrategy.mytime2hourMinSec(nowtime)
		nowSecs = h0*3600+m0*60+s0
		h, m, s = EnergyStrategy.mytime2hourMinSec(time)
		timeSecs = h*3600+m*60+s
		nbSecondsToNextRange = -nowSecs + timeSecs
		if nowtime>time: # It's next day
			nbSecondsToNextRange += 86400
		nextTime = now + timedelta(seconds=nbSecondsToNextRange)
		return nextTime
	@staticmethod
	def getTimeToWait(now, nextTime):
		if now>nextTime:
			wait = OffPeakManager.MIDNIGHT-now+nextTime
		else:
			wait = nextTime-now
		# print("getTimeToWait(",now,", ",nextTime,") = ",wait)
		return wait

	@staticmethod
	def getTime(strTime:str):
		"""
		Convert classic str time to 'mytime' type
		Exp : "10h00" => 100000
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
			raise Exception("Fail convert '%s' to Time." % strTime)
		return int(datetime.strptime(strTime, pattern).strftime("%H%M%S"))

	@staticmethod
	def parseOffPeakHoursRanges(offPeakHoursRanges):
		"""
		Parse configuration of offpeak: convert string to "mytime"
		"""
		offpeakHoursRanges = []
		for offpeakHoursRange in offPeakHoursRanges:
			begin = OffPeakManager.getTime(offpeakHoursRange[0])
			end = OffPeakManager.getTime(offpeakHoursRange[1])
			offpeakHoursRanges.append([begin, end])
		return offpeakHoursRanges

	def checkRange(self, nowDatetime: datetime=None) -> int
		"""
		Check if nowDatetime is in off-peak hours or not. 
		@return: tuple: (True if nowDatetime is in off-peak hours, range end time as Python datetime.)
		"""
		if nowDatetime is None:
			nowDatetime = datetime.now()
		now = self.datetime2Mytime(nowDatetime)
		# print("OffPeakStrategy.checkRange(",now,")")
		inOffpeakRange = False
		nextTime = now+EnergyStrategy.MIDNIGHT
		time2NextTime = EnergyStrategy.MIDNIGHT # This has no real signification but it's usefull and the most simple way
		for offpeakHoursRange in self.offpeakHoursRanges:
			begin, end = offpeakHoursRange
			wait = self.getTimeToWait(now, begin)
			if wait<time2NextTime:
				nextTime = begin
				time2NextTime = wait
				inOffpeakRange = False
			wait = self.getTimeToWait(now, end)
			if wait<time2NextTime:
				nextTime = end
				time2NextTime = wait
				inOffpeakRange = True
		assert nextTime<=240000
		rangeEnd = self.mytime2datetime(nowDatetime, nextTime)
		nbSecondsToNextRange = (self.rangeEnd - nowDatetime).total_seconds()
		self.logger.info("OffPeakManager.checkRange("+str(now)+") => "+str(self.rangeEnd)+ ", "+str(nbSecondsToNextRange))
		return (inOffpeakRange, rangeEnd)
	
	def inOffpeakRange(self, nowDatetime: datetime=None) -> bool:
		if nowDatetime is not None:
			return self.checkRange(nowDatetime)[0]
		else:
			if datetime.now()>self.rangeEnd:
				self.inOffpeakRange, self.rangeEnd = self.checkRange()
			return self.inOffpeakRange

	def getRangeEnd(self):
		return self.rangeEnd

