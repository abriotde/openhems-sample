"""
Custom and specific time management for OpenHEMS
"""

import re
import time
import logging
from datetime import datetime, timedelta
from .cast_utility import CastUtililty, CastException
from .configuration_manager import ConfigurationException

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
			raise NotImplementedError(f"Error Time() from incompatible type : '{type(atime)}'", )

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
	:param str hoursRangesList: list of ranges
	:param datetime timeStart: Before this date, this prices are not valid
	:param datetime timeout: After this date, this prices are not valid
	:param function timeoutCallBack: An object with implement getHoursRanges(nowDatetime, attime)
			function witch is called when timeout/timeStart occures
	:param float defaultCost: Cost for hoursRangesList when cost is not set.
	:param float outRangeCost: Cost ranges not defined in hoursRangesList
	"""
	def __init__(self, hoursRangesList:list=None, timeStart:datetime=None,
			  timeout:datetime=None, timeoutCallBack=None, data=None,
			  defaultCost:float=0.0, outRangeCost:float=0.15):
		if hoursRangesList is None:
			hoursRangesList = []
		self._index = 0
		self.ranges = []
		self.minCost = 0
		self.setHoursRangesList(hoursRangesList, defaultCost, outRangeCost)
		self.rangeEnd = datetime.now()
		self.timeout = timeout
		self.timeStart = timeStart
		self._timeoutCallBack = timeoutCallBack
		self.data=data


	def _fillRange(self, outRangeCost):
		"""
		Check for hole in self.ranges and fill it.
		Raise an exception if there is range cross.
		"""
		self.ranges.sort(key=lambda x: x[0].time)
		firstBegin = None
		lastEnd = None
		addedRange = []
		for begin, end, _ in self.ranges:
			if firstBegin is None:
				firstBegin = begin
			# print("range:", begin, end, "lastEnd:", lastEnd)
			if lastEnd is not None:
				if lastEnd.time<begin.time:
					addedRange.append([lastEnd, begin, outRangeCost])
				elif begin.time<lastEnd.time: # Should be equal
					raise ConfigurationException(f"HoursRanges : ranges are crossing : {begin} < {lastEnd}")
			lastEnd = end
		# Close the cycle from end to the begeining
		if lastEnd is not None and lastEnd.time!=firstBegin.time:
			addedRange.append([lastEnd, firstBegin, outRangeCost])
		if len(addedRange)>0:
			self.ranges += addedRange
		if len(self.ranges)==0: # Case no range
			self.ranges = [[Time(0), Time(Time.MIDNIGHT), outRangeCost]]

	def _extractRangeValues(self, offpeakHoursRange, defaultCost):
		begin = end = None
		cost = defaultCost
		if isinstance(offpeakHoursRange, list):
			if len(offpeakHoursRange) == 3:
				begin = offpeakHoursRange[0]
				end = offpeakHoursRange[1]
				cost = offpeakHoursRange[2]
			elif len(offpeakHoursRange) == 2:
				cost = offpeakHoursRange[1]
				if not isinstance(cost, (float, int)):
					begin = offpeakHoursRange[0]
					end = offpeakHoursRange[1]
					cost = defaultCost
				offpeakHoursRange = offpeakHoursRange[0]
			else:
				raise ConfigurationException(f"Invalid range format {offpeakHoursRange}")
		if isinstance(offpeakHoursRange, str):
			offpeakHoursRange = offpeakHoursRange.split("-")
		if begin is None:
			begin = offpeakHoursRange[0].strip()
		if end is None:
			end = offpeakHoursRange[1].strip()
		if not isinstance(begin, Time):
			begin = Time(begin)
		if not isinstance(end, Time):
			end = Time(end)
		return begin, end, cost

	def setHoursRangesList(self,
			hoursRangesList, defaultCost:float=0.0, outRangeCost:float=0.15):
		"""
		We can define only off-peak hours but we get full 24h range.
		Missing ranges are filled with outRangeCost (peak hours cost).
		When cost is not set in range, we consider it as defaultCost (offpeak hours cost).
		This function parse a list of ranges (2-tuple or 3-tuple) to convert it on Time
		Exp:
		[
			"22h-06h",
			["06h-10h",  0.12],
			[Time("10h")-Time("12h"), 0.2],
			["12h","16h", 0.13],
			["16h00","20h00"]
		]
		Result:
		[
			[22h, 06h, 0.0],
			[06h, 10h,  0.12],
			[10h, 12h, 0.2],
			[12h, 16h, 0.13],
			[16, 20h, 0.0],
			[20h, 22h, 0.15]
		]
		"""
		offpeaks = []
		if not isinstance(hoursRangesList, list):
			hoursRangesList = CastUtililty.toTypeList(hoursRangesList)
		for offpeakHoursRange in hoursRangesList:
			begin, end, cost = self._extractRangeValues(offpeakHoursRange, defaultCost)
			offpeaks.append([begin, end, cost])
		self.ranges = offpeaks
		# print("peakPeriods:", self.ranges)
		# check for hole
		self._fillRange(outRangeCost)
		self.ranges.sort(key=lambda x: x[0].time)
		# print("peakPeriods.2:", self.ranges)
		self.minCost = min(self.ranges, key=lambda x:x[2])[2]
		return self.ranges

	def checkRange(self, nowDatetime:datetime=None, attime:datetime=None):
		"""
		Check if nowDatetime (Default now) is in off-peak range (offpeakHoursRange)
		 and set end time of this range
		"""
		if nowDatetime is None:
			nowDatetime = datetime.now()
		# Check range validity of this housRange
		if ( (self.timeStart is not None and nowDatetime<self.timeStart)
				or (self.timeout is not None and self.timeout<nowDatetime)):
			return self._timeoutCallBack.getHoursRanges(nowDatetime, attime) \
				.checkRange(nowDatetime, attime)
		now = Time(nowDatetime)
		# print("OffPeakStrategy.checkRange(",now,")")
		inOffpeakRange = False
		nextTime = now.time+Time.MIDNIGHT
		# This has no real signification but it's usefull and the most simple way
		time2NextTime = Time.MIDNIGHT
		for hoursRange in self.ranges:
			_, end, _ = hoursRange
			wait = now.getTimeToWait(end)
			if wait<time2NextTime:
				nextTime = hoursRange
				time2NextTime = wait
		_, end, cost = nextTime
		self.rangeEnd = end.toDatetime(nowDatetime)
		inOffpeakRange = self.minCost==cost
		return (inOffpeakRange, self.rangeEnd, cost)

	def setLimits(self, timeStart=None, timeout=None):
		"""
		Change the timeout && timeStart
		"""
		self.timeout = timeout
		self.timeStart = timeStart

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
		offpeakHoursRanges = ""
		sep =""
		end = ""
		for begin, end, cost in self.ranges:
			offpeakHoursRanges += sep+str(begin)+" $"+str(cost)+" "
			sep =", "
		offpeakHoursRanges += str(end)
		return "["+offpeakHoursRanges+"]"
