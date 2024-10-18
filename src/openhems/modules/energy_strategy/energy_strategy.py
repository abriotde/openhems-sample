from datetime import datetime, timedelta
import time
import re
import logging
from modules.network.network import OpenHEMSNetwork

class EnergyStrategy:
	MIDNIGHT = 240000
	def  __init__(self):
		pass

	def updateNetwork(self):
		logging.getLogger("EnergyStrategy").error("EnergyStrategy.updateNetwork() : To implement in sub-class")

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
			wait = EnergyStrategy.MIDNIGHT-now+nextTime
		else:
			wait = nextTime-now
		# print("getTimeToWait(",now,", ",nextTime,") = ",wait)
		return wait

