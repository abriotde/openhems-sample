"""
Super class for all EnergyStrategy modules
"""
from datetime import datetime, timedelta
import logging
# from openhems.modules.network.network import OpenHEMSNetwork
LOOP_DELAY_VIRTUAL = 0

class EnergyStrategy:
	"""
	Super class for all EnergyStrategy modules
	"""
	MIDNIGHT = 240000
	def  __init__(self):
		pass

	# pylint: disable=unused-argument
	def updateNetwork(self, cycleDuration):
		"""
		Function to update OpenHEMSNetwork. To implement in sub-class
		"""
		logging.getLogger("EnergyStrategy")\
			.error("EnergyStrategy.updateNetwork() : To implement in sub-class")

	@staticmethod
	def datetime2Mytime(dtime: datetime):
		"""
		Convert standard Python datetime to custom "Mytime" type used for comparaison
		"""
		return int(dtime.strftime("%H%M%S"))
	@staticmethod
	def mytime2hourMinSec(mytime):
		"""
		Extract [hours, min, secs] from custom "Mytime" type
		"""
		secs = mytime%100
		mymin = int(mytime/100)%100
		hours = int(mytime/10000)
		return  [hours, mymin, secs]
	@staticmethod
	def mytime2datetime(now: datetime, mytime):
		"""
		Convert custom "Mytime" (used for comparaison) type to standard Python datetime
		 now is used to get next "mytime" because mytime
		  do not keep information about date
		"""
		nowtime = EnergyStrategy.datetime2Mytime(now)
		h0, m0, s0 = EnergyStrategy.mytime2hourMinSec(nowtime)
		nowSecs = h0*3600+m0*60+s0
		h, m, s = EnergyStrategy.mytime2hourMinSec(mytime)
		timeSecs = h*3600+m*60+s
		nbSecondsToNextRange = -nowSecs + timeSecs
		if nowtime>mytime: # It's next day
			nbSecondsToNextRange += 86400
		nextTime = now + timedelta(seconds=nbSecondsToNextRange)
		return nextTime
	@staticmethod
	def getTimeToWait(now, nextTime):
		"""
		Return an abstract time to compare times.
		"""
		if now>nextTime:
			wait = EnergyStrategy.MIDNIGHT-now+nextTime
		else:
			wait = nextTime-now
		# print("getTimeToWait(",now,", ",nextTime,") = ",wait)
		return wait
