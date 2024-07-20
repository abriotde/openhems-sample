from datetime import datetime, timedelta
import time
import re
from openhems_node import OpenHEMSNetwork

class EnergyStrategy:
	def updateNetwork(self):
		print("EnergyStrategy.updateNetwork() : To implement in sub-class")

class OffPeakStrategy(EnergyStrategy):
	"""
	This is in case we just base on "off-peak" range hours to control output. Classic use-case is some grid contract (Like Tempo on EDF).
	"""
	MIDNIGHT = 240000
	offpeakHoursRanges = []
	inOffpeakRange = False
	rangeEnd = datetime.now()
	network = None

	def __init__(self, network: OpenHEMSNetwork, offpeakHoursRanges=[["22:00:00","06:00:00"]]):
		print("OffPeakStrategy(",offpeakHoursRanges,")")
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
		nowtime = OffPeakStrategy.datetime2Mytime(now)
		h0, m0, s0 = OffPeakStrategy.mytime2hourMinSec(nowtime)
		nowSecs = h0*3600+m0*60+s0
		h, m, s = OffPeakStrategy.mytime2hourMinSec(time)
		timeSecs = h*3600+m*60+s
		nbSecondsToNextRange = -nowSecs + timeSecs
		if nowtime>time: # It's next day
			nbSecondsToNextRange += 86400
		nextTime = now + timedelta(seconds=nbSecondsToNextRange)
		return nextTime
	@staticmethod
	def getTimeToWait(now, nextTime):
		if now>nextTime:
			wait = OffPeakStrategy.MIDNIGHT-now+nextTime
		else:
			wait = nextTime-now
		# print("getTimeToWait(",now,", ",nextTime,") = ",wait)
		return wait
		
	
	def checkRange(self, nowDatetime: datetime=None) -> int:
		if nowDatetime is None:
			nowDatetime = datetime.now()
		now = self.datetime2Mytime(nowDatetime)
		# print("OffPeakStrategy.checkRange(",now,")")
		self.inOffpeakRange = False
		nextTime = now+OffPeakStrategy.MIDNIGHT
		time2NextTime = OffPeakStrategy.MIDNIGHT # This has no real signification but it's usefull and the most simple way
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
		print("OffPeakStrategy.checkRange(",now,") => ", self.rangeEnd, ", ", nbSecondsToNextRange)
		return nbSecondsToNextRange

	def sleepUntillNextRange(self):
		MARGIN = 1 # margin to wait more to be sure to change range... useless, not scientist?
		time2wait = (self.rangeEnd - datetime.now()).total_seconds()
		print("OffPeakStrategy.sleepUntillNextRange() : sleep(",round((time2wait+MARGIN)/60)," min, until ",self.rangeEnd,")")
		time.sleep(time2wait+MARGIN)

	def switchOffAll(self):
		print("OffPeakStrategy.switchOffAll()")
		self.network.print()
		powerMargin = self.network.getCurrentPower()
		self.network.print()
		ok = True
		for elem in self.network.out:
			if elem.isSwitchable and elem.switchOn(False):
				print("Warning : Fail to switch off ",elem.id)
				ok = False
		return ok

	def switchOn(self, node, cycleDuration, doSwitchOn=True):
		if node.isSwitchable:
			if node.isOn():
				lastDuration = node.getSchedule().decreaseTime(cycleDuration)
				print("Node ",node.id," isOn for ", lastDuration, " more seconds")
				if lastDuration==0:
					print("Info : Switch off ",node.id," due to elapsed time.")
					if node.switchOn(False):
						print("Warning : Fail switch off ",node.id,".")
			elif doSwitchOn and node.getSchedule().isScheduled():
				if node.switchOn(True):
					print("Info : Switch on ",node.id," successfully.")
					return True
				else:
					print("Warning : Fail switch on ",node.id,".")
		return False

	def switchOnMax(self, cycleDuration):
		print("OffPeakStrategy.switchOnMax()")
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
			if self.switchOffAll():
				self.sleepUntillNextRange()
				self.checkRange() # To update self.rangeEnd (and should change self.inOffpeakRange)
			else:
				print("Warning : Fail to swnitch off all. We will try again on next loop.")

# Linky case: switch-on on solar production.
class SolarOnlyProductionStrategy(EnergyStrategy):
	"""
	Case we have just solar panel (and battery) as electricity source
	"""
	def __init__(self, network: OpenHEMSNetwork):
		print("SolarOnlyProductionStrategy()")
		# TODO
	def updateNetwork(self, cycleDuration):
		print("SolarOnlyProductionStrategy.updateNetwork() : TODO")
		pass
		# TODO

# Linky case: switch-on on solar production and check no sell to linky.
class SolarNoSellProduction(EnergyStrategy):
	"""
	Case we have solar panel (and battery) and public grid as source but we can't sell. We may have battery, if so we will disconnect public grid to insure ther is no sell.
	"""
	def __init__(self, network: OpenHEMSNetwork):
		print("SolarNoSellProduction()")
		# TODO

	def updateNetwork(self, cycleDuration):
		print("SolarNoSellProduction.updateNetwork() : TODO")
		pass
		# TODO

