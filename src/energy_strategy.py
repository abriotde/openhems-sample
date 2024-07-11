from datetime import datetime
import time
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
	def datetime2Mytime(time):
		return int(datetime.now().strftime("%H%M%S"))
	@staticmethod
	def mytime2Seconds(time):
		secs = time%100
		min = int(time/100)%100
		hours = int(time/10000)
		ret = hours*3600+min*60+secs
		# print("mytime2Seconds(",time,") = ", ret)
		return ret
	@staticmethod
	def getTimeToWait(now, nextTime):
		if now>nextTime:
			return OffPeakStrategy.MIDNIGHT-now+nextTime
		return nextTime-now
	
	def checkRange(self, now=None):
		if now is None:
			now = self.datetime2Mytime(datetime.now())
		# print("OffPeakStrategy.checkRange(",now,")")
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

	def sleepUntillNextRange():
		MARGIN = 1 # margin to wait more to be sure to change range... useless, not scientist?
		now = self.datetime2Mytime(datetime.now())
		time2wait = self.getTimeToWait(now, self.rangeEnd)
		print("OffPeakStrategy.sleepUntillNextRange() : sleep(",(time2wait+MARGIN)/60," min)")
		time.sleep(self.mytime2Seconds(time2wait+MARGIN))

	def updateNetwork(self):
		self.homeStateUpdater.updateStates()
		if self.inOffpeakRange:
			# We are in off-peak range hours : switch on all
			# TODO self.switchOnMax()
			pass
		else: # Sleep untill end.
			# TODO self.switchOffAll()
			self.sleepUntillNextRange()
			self.checkRange() # To update self.rangeEnd (and should change self.inOffpeakRange)

# Linky case: switch-on on solar production.
class SolarOnlyProductionStrategy(EnergyStrategy):
	"""
	Case we have just solar panel (and battery) as electricity source
	"""
	def __init__(self, network: OpenHEMSNetwork):
		print("SolarOnlyProductionStrategy()")
		# TODO
	def updateNetwork(self):
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
	def updateNetwork(self):
		pass
		# TODO

