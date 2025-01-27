"""
Custom and specific time management for OpenHEMS
"""

import re
import time
import logging
from datetime import datetime, timedelta
from .cast_utility import CastException
# from openhems.modules.util.cast_utility import CastException
logger = logging.getLogger(__name__)

# Time to wait in seconds before considering to be in offpeak range
TIME_MARGIN_IN_S = 1
DATETIME_PRINT_FORMAT = "%Y-%m-%d %H:%M:%S"

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

	def __init__(self, atime):
		if isinstance(atime, datetime):
			self.time = self._fromDatetime(atime)
		elif isinstance(atime, str):
			self.time = self._fromStr(atime)
		elif isinstance(atime, int):
			self.time = atime
		else:
			logger.error("Error Time() from incompatible type")

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
		return str(h).rjust(2, "0")+"h"+(str(m).rjust(2, "0"))

	def __repr__(self):
		h, m, _ = self.toHourMinSec()
		return str(h).rjust(2, "0")+":"+(str(m).rjust(2, "0"))

	def __eq__(self, other):
		return self.time == other.time

class HoursRanges:
	"""
	Class to represent and manipulate hours range:
	- Sort and order => make it unique
	- Reverse it
	- Parse from strings
	- Check if a datetime is in or out
	"""
	def __init__(self, offPeakHoursRanges:list):
		self._index = 0
		self.setOffPeakHoursRanges(offPeakHoursRanges)
		self.rangeEnd = datetime.now()

	def setOffPeakHoursRanges(self, offPeakHoursRanges):
		"""
		Parse a list of ranges (2-tuple or String) to convert it on Time
		"""
		offpeaks = []
		for offpeakHoursRange in offPeakHoursRanges:
			if isinstance(offpeakHoursRange, str):
				offpeakHoursRange = offpeakHoursRange.split("-")
			begin = offpeakHoursRange[0]
			if not isinstance(begin, Time):
				begin = Time(begin)
			end = offpeakHoursRange[1]
			if not isinstance(end, Time):
				end = Time(end)
			offpeaks.append([begin, end])
		self.ranges = offpeaks

	def getReverse(self):
		"""
		Reverse the range : Usefull for Emhass which need peekHours.
		(getPeakHoursRanges() is too confusing name)
		Applying twice this function should give back the same.
		"""
		# TODO Sort/merge ?
		reverse = []
		first = None # Keep the first
		start = None
		for r in self.ranges:
			if first is None:
				first = r[0]
			else:
				# The previous start is now the end, and reverse
				reverse.append([start, r[0]])
			start = r[1]
		if first is not None:
			reverse.append([start, first])
		return HoursRanges(reverse)

	def checkRange(self, nowDatetime: datetime=None):
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
		for hoursRange in self.ranges:
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
		self.rangeEnd = Time(nextTime).toDatetime(nowDatetime)
		# nbSecondsToNextRange = (self.rangeEnd - nowDatetime).total_seconds()
		# logger.info("OffPeakStrategy.checkRange({now}) => %s, %d", \
		# 	rangeEnd, nbSecondsToNextRange)
		return (inOffpeakRange, self.rangeEnd)

	def isEmpty(self):
		"""
		Return True if there is no range.
		"""
		return len(self.ranges)<=0

	def getTime2NextRange(self, now) -> int:
		"""
		Return: time to wait in seconds untils next range
		"""
		return (self.rangeEnd - now).total_seconds()

	def sleepUntillNextRange(self, now):
		"""
		Set application to sleep until off-peak (or inverse) range end
		TIME_MARGIN_IN_S: margin to wait more to be sure to change range... 
		useless, not scientist?
		"""
		time2wait = self.getTime2NextRange(now)
		logger.info("sleepUntillNextRange() : sleep(%d min, until %s)",\
			round((time2wait+TIME_MARGIN_IN_S)/60), str(self.rangeEnd))
		time.sleep(time2wait+TIME_MARGIN_IN_S)

	def __iter__(self):
		self._index = 0
		return self

	def __next__(self):
		if self._index<len(self.ranges):
			r = self.ranges[self._index]
			self._index += 1
			return r
		raise StopIteration

	def __str__(self):
		return str(self.ranges)
