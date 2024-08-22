from datetime import datetime, timedelta
import time
import re
import logging
from network import OpenHEMSNetwork

class EnergyStrategy:
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


# Case only grid source : Switch on max on off-peak hours (Without exceed max authorized).
from energy_strategy.offpeak_strategy import OffPeakStrategy

# Case dual-source : "source inverter" and MPPT : Use grid energy when battery level is low and solar production less than consumption; Reverse if battery level is medium and/or solar production higher than conumption
import energy_strategy.sourceinverter_strategy
# Case dual-source : "hybrid inverter with security mode" : 
import energy_strategy.hybridinverter_strategy
# Try nether put electricity on grid. security with a source inverter to disconnect grid?
import energy_strategy.solarnosell_strategy

# Case off-grid: minimize battery solicitation
import energy_strategy.offgrid_strategy

