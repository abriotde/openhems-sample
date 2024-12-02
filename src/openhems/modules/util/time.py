"""
Custom and specific time management for OpenHEMS
"""

import re
from datetime import datetime, timedelta
from .cast_utility import CastException
# from openhems.modules.util.cast_utility import CastException

class Time:
	"""
	Class to manage offpeak-hours and all time based information
	 without considering the date.
	"""
	MIDNIGHT = 240000

	@staticmethod
	def _fromDatetime(dtime: datetime):
		"""
		Convert standard Python datetime to custom "Mytime" type used for comparaison
		"""
		return int(dtime.strftime("%H%M%S"))
	@staticmethod
	def _fromStr(strTime:str):
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
			raise CastException(f"Fail convert '{strTime}' to Time.", "")
		return int(datetime.strptime(strTime, pattern).strftime("%H%M%S"))

	def __init__(self, time):
		if isinstance(time, datetime):
			self.time = self._fromDatetime(time)
		elif isinstance(time, str):
			self.time = self._fromStr(time)
		elif isinstance(time, int):
			self.time = time
		else:
			print("Error Time() from incompatible type")

	def toHourMinSec(self):
		"""
		Extract [hours, min, secs] from custom "Mytime" type
		"""
		secs = self.time%100
		mymin = int(self.time/100)%100
		hours = int(self.time/10000)
		return  [hours, mymin, secs]

	def toDatetime(self, now: datetime):
		"""
		Convert custom "Time" (used for comparaison) type to standard Python datetime
		 now is used to get next "Time" because Time
		  do not keep information about date
		"""
		nowtime = Time(now)
		h0, m0, s0 = nowtime.toHourMinSec()
		nowSecs = h0*3600+m0*60+s0
		h, m, s = self.toHourMinSec()
		timeSecs = h*3600+m*60+s
		nbSecondsToNextRange = -nowSecs + timeSecs
		if nowtime.time>self.time: # It's next day
			nbSecondsToNextRange += 86400
		nextTime = now + timedelta(seconds=nbSecondsToNextRange)
		return nextTime

	def getTimeToWait(self, nextTime):
		"""
		Return an abstract time to compare times.
		"""
		if self.time>nextTime.time:
			wait = self.MIDNIGHT-self.time+nextTime.time
		else:
			wait = nextTime.time-self.time
		# print("getTimeToWait(",self.time,", ",nextTime,") = ",wait)
		return wait

	def __str__(self):
		h, m, _ = self.toHourMinSec()
		return str(h)+"h"+(str(m).rjust(2, "O"))

	def __repr__(self):
		h, m, _ = self.toHourMinSec()
		return str(h)+"h"+(str(m).rjust(2, "O"))

	@staticmethod
	def getOffPeakHoursRanges(offPeakHoursRanges):
		"""
		Parse a list of ranges (2-tuple or String) to convert it on Time
		"""
		offpeaks = []
		for offpeakHoursRange in offPeakHoursRanges:
			if isinstance(offpeakHoursRange, str):
				offpeakHoursRange = offpeakHoursRange.split("-")
			begin = Time(offpeakHoursRange[0])
			end = Time(offpeakHoursRange[1])
			offpeaks.append([begin, end])
		return offpeaks

	@staticmethod
	def checkRange(hoursRanges:list, nowDatetime: datetime=None):
		"""
		Check if nowDatetime (Default now) is in off-peak range (offpeakHoursRange)
		 and set end time of this range
		"""
		if nowDatetime is None:
			nowDatetime = datetime.now()
		now = Time(nowDatetime)
		# print("OffPeakStrategy.checkRange(",now,")")
		inOffpeakRange = False
		nextTime = now.time+Time.MIDNIGHT
		# This has no real signification but it's usefull and the most simple way
		time2NextTime = Time.MIDNIGHT
		for hoursRange in hoursRanges:
			begin, end = hoursRange
			wait = now.getTimeToWait(begin)
			if wait<time2NextTime:
				nextTime = begin.time
				time2NextTime = wait
				inOffpeakRange = False
			wait = now.getTimeToWait(end)
			if wait<time2NextTime:
				nextTime = end.time
				time2NextTime = wait
				inOffpeakRange = True
		assert nextTime<=240000
		rangeEnd = Time(nextTime).toDatetime(nowDatetime)
		# nbSecondsToNextRange = (self.rangeEnd - nowDatetime).total_seconds()
		# logger.info("OffPeakStrategy.checkRange({now}) => %s, %d", \
		# 	rangeEnd, nbSecondsToNextRange)
		return (inOffpeakRange, rangeEnd)
