#!/usr/bin/env python3
import time
import re
from datetime import datetime

class HomeStateUpdater:
	def updateStates(self):
		pass

class EnergyStrategy:
	def updateNetwork(self):
		pass

class OffPeakStrategy:
	MIDNIGHT = 240000
	offpeakHoursRanges = []
	inOffpeakRange = False
	rangeEnd = datetime.now()
	
	def __init__(self, offpeakHoursRanges=[["22:00:00","06:00:00"]]):
		print("OffPeakStrategy(",offpeakHoursRanges,")")
		self.setOffPeakHoursRanges(offpeakHoursRanges)
		self.checkRange()
		
	@staticmethod
	def getTime(strTime:str):
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

	@staticmethod
	def getTimeToWait(now, nextTime):
		if now>nextTime:
			return OffPeakStrategy.MIDNIGHT-now+nextTime
		return nextTime-now
	def checkRange(self, now=None):
		if now is None:
			now = int(datetime.now().strftime("%H%M%S"))
		print("OffPeakStrategy.checkRange(",now,")")
		self.inOffpeakRange = False
		nextTime = now+OffPeakStrategy.MIDNIGHT
		time2NextTime = OffPeakStrategy.MIDNIGHT
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
		self.rangeEnd = nextTime

	def updateNetwork(self):
		pass

class SunRiseStrategy:
	def updateNetwork(self):
		pass


class OpenHomeEnergyManagementServer:

	def __init__(self, homeStateUpdater: HomeStateUpdater) -> None:
		self.homeStateUpdater = homeStateUpdater
		

	# Update the home energy state : all changed elements.
	def updateState(self):
		self.homeStateUpdater.updateStates()
		# find E demand
		# predict E cost/production
		# 
	
	# 
	def loop(self):
		self.updateState()
		self
		

	# Run an infinite loop where each loop shouldn't last more than loopTime and will never last less than loopTime
	def run(self, loopTime=60):
		nextloop = time.time() + loopTime
		while True:
			self.loop()
			t = time.time()
			if t<nextloop:
				time.sleep(nextloop-t)
				t = time.time()
			elif t>nextloop:
				print("Warning : OpenHomeEnergyManagement::run() : missing time for loop : ", (t-nextloop), "seconds")
			nextloop = t + loopTime
