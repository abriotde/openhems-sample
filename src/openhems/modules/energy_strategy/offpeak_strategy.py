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
		super().__init__(strategyId, network, mylogger, True)
		self.inOffpeakRange = False
		self.rangeEnd = datetime.now()
		self.offpeakHoursRanges = self.network.getOffPeakHoursRanges()
		self.logger.info("OffPeakStrategy(%s) on %s", str(self.offpeakHoursRanges), str(self.getNodes()))
		if not self.offpeakHoursRanges:
			msg = "OffPeak-strategy is useless without offpeak hours. Check your configuration."
			self.logger.critical(msg)
			raise ConfigurationException(msg)
		self._rangeChangeDone = False
		self.nextRanges = [] # List of tuples (inoffpeakTime, rangeEndDatetime)
		# witch represent next offpeak periods
		self.checkRange()

	def checkRange(self, nowDatetime: datetime=None) -> int:
		"""
		Check if nowDatetime (Default now) is in off-peak range (offpeakHoursRange)
		 and set end time of this range
		"""
		if nowDatetime is None:
			nowDatetime = datetime.now()
		offpeakranges = self.offpeakHoursRanges
		inoffpeakPrev = self.inOffpeakRange
		self.offpeakHoursRanges = self.network.getOffPeakHoursRanges()
		useCache = False
		if offpeakranges!=self.offpeakHoursRanges:
			self.nextRanges = []
		else:
			# use cache
			for range in self.nextRanges:
				inoffpeak, rangeEnd = range
				if rangeEnd>nowDatetime:
					self.inOffpeakRange = inoffpeak
					self.rangeEnd = rangeEnd
					useCache = True
					break
		self.inOffpeakRange, self.rangeEnd = self.offpeakHoursRanges.checkRange(nowDatetime)
		if inoffpeakPrev!=self.inOffpeakRange:
			self._rangeChangeDone = False
			if useCache:
				# Remove old ranges from self.nextRanges
				self.nextRanges = filter(lambda r: nowDatetime>r[1], self.nextRanges)
		if len(self.nextRanges)==0:
			self.nextRanges = [
				(self.inOffpeakRange, self.rangeEnd)
			]

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
			self.check4MissingOffeakTime(now, cycleDuration)

	def getMissingTime(self, schedule, now):
		"""
		Evaluate if a schedule can't be honor during offpeak periods only (regarding timeout)
		Return: Time in seconds to switch on during peak periods.
		"""
		missingTime = 0
		if schedule.duration>0 and schedule.timeout is not None:
			i = 0
 			nbPeakPeriods = 0
			previousRangeEnd = now
			times = (0, 0, previousRangeEnd) # Tuple of time in seconds during offpeak
			while previousRangeEnd is not None and schedule.timeout>previousRangeEnd:
				if i>len(self.nextRanges):
					range = self.offpeakHoursRanges.checkRange(previousRangeEnd)
					self.nextRanges.append(range)
				else:
					range = self.nextRanges[i]
				i += 1
				times = self.updateTimes(schedule, range, times)
				offpeakTime, peakTime, previousRangeEnd = times
			missingTime = schedule.duration*1.1 - offpeakTime 
			# Marge of 10% for duration for safety, 
			# for case of electricity overload and need to stop devices.
			# TODO: set this margin in configuration
			if missingTime>peakTime:
				self.logger.warning("Missing %d minutes to respect timeout.", 
					                    round((missingTime-peakTime)/60), 2)
		return missingTime

	def check4MissingOffeakTime(self, now, cycleDuration):
		"""
		Switch on nodes wich must be switch on during peak-periods
		due to missing time during offpeak period to respect timeout
		"""
		# TODO : A better solution should be to not iterate over all nodes and ask getStrategyCache()
		# Maybe a way to remove OffPeakStrategy cache directly... a callback?
		for elem in self.getNodes():
			schedule = node.getSchedule()
 			onPeriods = schedule.getStrategyCache(self.strategyId)
 			if onPeriods is None:
				onPeriods = self.getOnPeriods(now, schedule)
				schedule.setStrategyCache(self.strategyId, onPeriods)
			for onPeriod in onPeriods:
				start, end = onPeriods[0]
				if now>start:
					if end>now:
						if self.switchOnSchedulable(elem, cycleDuration, True):
							done += 1
					else:
						self.switchOnSchedulable(elem, cycleDuration, False)
						# TODO : remove past periods : useless anymore
						schedule.setStrategyCache(self.strategyId, onPeriods)

 	def getOnPeriods(self, now, schedule)
 		"""
		Check a schedule wich must be switch on during peak-time
		due to missing time during offpeak period to respect timeout
		return: List of periods to switch on device during peaktime.
 		"""
		missingTime = self.getMissingTime(now, schedule)
		if 0>=missingTime:
			return []
		# Determine when there is peakperiods and theire cost
		peakPeriods = []
		i = 0
		previousRangeEnd = now
		ok = True
		while len(self.nextRanges)>i and ok:
			inoffpeak, rangeEnd = self.nextRanges[i]
			if rangeEnd>schedule.timeout:
				ok = False
				rangeEnd = schedule.timeout
			if not inoffpeak:
				availableTime = rangeEnd - previousRangeEnd
				cost = self.network.estimateKwhCost(rangeEnd - (availableTime/2))
				peakPeriods.append([previousRangeEnd, availableTime, rangeEnd, cost])
			previousRangeEnd = rangeEnd
			i++
		# Choice when to start/stop: So choice the best periods
		onPeriods = []
		peakPeriods = peakPeriods.sort(key=lambda x:x[3]) # Sort by cost
		i = 0
		while missingTime>0:
			start, duration, end, cost = peakPeriod[i]
			if duration>missingTime:
				missingTime = 0
				end = start + missingTime
			else:
				missingTime -= peakPeriod[1]
			onPeriods.append([start, end]) # Sort by start time
			i += 1
		onPeriods = onPeriods.sort(key=lambda x:x[0])
		schedule.setStrategyCache(onPëriods)
		return onPeriods

	def updateTimes(self, schedule, range, times:tuple):
		(offpeakTime, peakTime, previousRangeEnd) = times
		if schedule.timeout>previousRangeEnd:
			inoffpeak, rangeEnd = range
			if schedule.timeout>rangeEnd:
				additionalTime = rangeEnd - previousRangeEnd
			else:
				additionalTime = schedule.timeout - previousRangeEnd
			if inoffpeak:
				offpeakTime += additionalTime
			else:
				peakTime += additionalTime
			previousRangeEnd = rangeEnd
			return (offpeakTime, peakTime, previousRangeEnd)
		return (offpeakTime, peakTime, None)

