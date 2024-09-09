from datetime import datetime, timedelta
import time
import re
import logging
from modules.network.network import OpenHEMSNetwork
from .energy_strategy import EnergyStrategy
from .offpeak_manager import OffPeakManager

class OffPeakStrategy(EnergyStrategy):
	"""
	This is in case we just base on "off-peak" range hours to control output. Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours with check to not exceed authorized max consumption
	"""
	offpeakHoursRanges = []
	inOffpeakRange = False
	rangeEnd = datetime.now()
	network = None

	def __init__(self, network: OpenHEMSNetwork, offpeakHoursRanges=[["22:00:00","06:00:00"]]):
		self.logger = logging.getLogger(__name__)
		self.logger.info("OffPeakStrategy("+str(offpeakHoursRanges)+")")
		self.network = network
		self.offpeakManager = OffPeakManager(offpeakHoursRanges)

	def sleepUntillNextRange(self):
		MARGIN = 1 # margin to wait more to be sure to change range... useless, not scientist?
		time2wait = (self.offpeakManager.getRangeEnd() - datetime.now()).total_seconds()
		self.logger.info("OffPeakStrategy.sleepUntillNextRange() : sleep("+str(round((time2wait+MARGIN)/60))+" min, until "+str(self.rangeEnd)+")")
		time.sleep(time2wait+MARGIN)


	def switchOn(self, node, cycleDuration, doSwitchOn=True):
		if node.isSwitchable:
			if node.isOn():
				power = node.getCurrentPower()
				schedule = node.getSchedule()
				more = schedule.decreaseTime(cycleDuration, power)
				self.logger.debug("Node "+node.id+" isOn for "+str(lastDuration)+" more seconds")
				if schedule.isScheduled():
					self.logger.info("Switch off '"+str(node.id)+"' due to elapsed time.")
					if node.switchOn(False):
						self.logger.warning("Fail switch off "+node.id+".")
			elif doSwitchOn and node.getSchedule().isScheduled():
				if node.switchOn(True):
					self.logger.info("Switch on '"+str(node.id)+"' successfully.")
					return True
				else:
					self.logger.warning("Fail switch on "+node.id+".")
		return False

	def switchOnMax(self, cycleDuration):
		self.logger.info("OffPeakStrategy.switchOnMax()")
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
		if self.offpeakManager.inOffpeakRange():
			# We are in off-peak range hours : switch on all
			self.switchOnMax(cycleDuration)
		else: # Sleep untill end. 
			if self.network.switchOffAll():
				self.sleepUntillNextRange()
			else:
				print("Warning : Fail to swnitch off all. We will try again on next loop.")

