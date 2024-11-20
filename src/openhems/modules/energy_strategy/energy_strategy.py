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
	def  __init__(self, strategy, logger=None):
		if logger is None:
			logger = logging.getLogger(__name__)
		self.logger = logger
		self.id = strategy.get('id', None)
		if self.id is None:
			self.logger.error("No 'id' attribute for strategy.")

	# pylint: disable=unused-argument
	def updateNetwork(self, cycleDuration):
		"""
		Function to update OpenHEMSNetwork. To implement in sub-class
		"""
		logging.getLogger("EnergyStrategy")\
			.error("EnergyStrategy.updateNetwork() : To implement in sub-class")

	def switchOn(self, node, cycleDuration, doSwitchOn):
		"""
		Switch on/off the node depending on doSwitchOn.
		IF the node is ever on:
		 - decrement his time to be on from cycleDuration
		 - Switch off the node if time to be on elapsed
		    or strategy choice is to switch off
		ELSE IF doSwitchOn=True: Switch on the node
		"""
		if node.isSwitchable:
			if node.isOn():
				remainingTime = node.getSchedule().decreaseTime(cycleDuration)
				if remainingTime==0 or not doSwitchOn:
					self.logger.info("Switch off '%s' due to %s.",
						node.id, "elapsed time" if remainingTime==0 else "strategy")
					if node.switchOn(False):
						self.logger.warning("Fail switch off '%s'.", node.id)
				else:
					self.logger.debug("Node %s isOn for %s more seconds", \
						node.id, remainingTime)
			else:
				if doSwitchOn and node.getSchedule().duration>0:
					if node.switchOn(True):
						self.logger.info("Switch on '%s' successfully.", node.id)
						return True
					self.logger.warning("Fail switch on '%s'.", node.id)
				else:
					self.logger.debug("Node '%s' is off and not schedule for %d secondes.",
						node.id, node.getSchedule().duration)
		else:
			self.logger.debug("switchOn() : Node is not switchable : %s.", node.id)
		return False

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
