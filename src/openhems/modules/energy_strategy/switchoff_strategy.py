"""
This is in case we just base on "off-peak" range hours to control output.
	 Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours
"""

from datetime import datetime
from openhems.modules.network.network import OpenHEMSNetwork
from openhems.modules.util import ConfigurationException, HoursRanges
from .energy_strategy import EnergyStrategy, LOOP_DELAY_VIRTUAL


# pylint: disable=broad-exception-raised
class SwitchoffStrategy(EnergyStrategy):
	"""
	This is in case we just base on "off-peak" range hours to control output.
	 Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours
	 with check to not exceed authorized max consumption
	"""

	def __init__(self, mylogger, network: OpenHEMSNetwork, strategyId:str,
		     offHoursRanges, reverse=False):
		super().__init__(strategyId, mylogger)
		self.network = network
		self.offHoursRanges = HoursRanges(offHoursRanges)
		self.inOffRange = False
		self._rangeEnd = datetime.now()
		self._rangeChangeDone = False
		self._todo = self.getNodes()
		self._backupStates = {}
		self.reverse = reverse
		self.logger.info("Switch%sStrategy(%s) on %s", "On" if reverse else "Off",
		                 str(self.offHoursRanges), str(self._todo))
		if not self.offHoursRanges:
			msg = "OffPeak-strategy is useless without offpeak hours. Check your configuration."
			self.logger.critical(msg)
			raise ConfigurationException(msg)
		self.checkRange()

	def checkRange(self, nowDatetime: datetime=None) -> int:
		"""
		Check if nowDatetime (Default now) is in off-peak range (offpeakHoursRange)
		 and set end time of this range
		"""
		inOff = self.inOffRange
		self.inOffRange, self._rangeEnd = self.offHoursRanges.checkRange(nowDatetime)
		if inOff!=self.inOffRange:
			self._rangeChangeDone = False
			self._todo = self.getNodes()

	def switchOn(self, node, cycleDuration, doSwitchOn:bool=True):
		"""
		Switch on/off the node depending on doSwitchOn.
		IF the node is ever on:
		 - decrement his time to be on from cycleDuration
		 - Switch off the node if time to be on elapsed
		    or strategy choice is to switch off
		ELSE IF doSwitchOn=True: Switch on the node
		"""
		del cycleDuration
		# print("SwitchoffStrategy.switchOn()")
		if node.isSwitchable:
			isOn = node.isOn()
			isOnStr = "on" if isOn else "off"
			if doSwitchOn ^ isOn: # If we need to toogle switch (isOn!=doSwitchOn)
				switchStr = "on" if doSwitchOn else "off"
				if node.switchOn(doSwitchOn):
					self.logger.warning("Fail switch %s '%s'.", switchStr, node.id)
					return False
				else:
					self.logger.info("Switch %s '%s' successfully", \
						switchStr, node.id)
			else:
				self.logger.debug("Let node '%s' %s", node.id, isOnStr)
		else:
			self.logger.debug("Not switchable node : '%s'.", node.id)
		return True

	def switchOnAll(self, switchOn=True):
		"""
		Switch on nodes, but 
		 - If there is no margin to switch on, do nothing.
		 - Only one (To be sure to not switch on to much devices)
		"""
		self.logger.info("SwitchoffStrategy.%s.switchOnAll(%s)", self.strategyId, switchOn)
		marginPower = self.network.getMarginPowerOn()
		if marginPower<0:
			self.logger.info("Can't switch on devices: not enough power margin : %s", marginPower)
			return False
		todo = []
		for elem in self._todo:
			if (not switchOn) ^ self.reverse: # Start of period : remember states
				isOn = elem.isOn()
				self._backupStates[elem.id] = isOn
				if isOn==switchOn:
					_switchOn = None
					msg = "Node is ever "+("on" if switchOn else "off")+". NB : It will be let as is at the end period."
				else:
					_switchOn = switchOn
			else: # End of period : restore states
				_switchOn = self._backupStates.get(elem.id, None)
				msg = ""
				if (not _switchOn) ^ self.reverse:
					# We should expect switch on at end of switchOff period,
					# but as we restore as the start, we switch off
					# (and the opposite on reverse case)
					self.logger.info("Restore the state : %s for %s", ("on" if _switchOn else "off"), elem.id)
			if _switchOn is None:
				self.logger.info("SwitchoffStrategy(%s) : Nothing to do for '%s'. %s",
				                  self.strategyId, elem.id, msg)
			else:
				if not self.switchOn(elem, 0, _switchOn):
					todo.append(elem)
		self._todo = todo
		return len(self._todo)==0

	def updateNetwork(self, cycleDuration:int, allowSleep:bool, now=None) -> int:
		"""
		Decide what to do during the cycle:
		 IF off-peak : switch on all
		 ELSE : Switch off all AND Sleep until off-peak
		"""
		if now is None:
			now = datetime.now()
		if now>=self._rangeEnd:
			self.checkRange()
		if not self._rangeChangeDone:
			if self.switchOnAll(not(self.inOffRange ^ self.reverse)):
				if cycleDuration>LOOP_DELAY_VIRTUAL and allowSleep:
					self.offHoursRanges.sleepUntillNextRange(now)
					self.checkRange() # To update self._rangeEnd (and should change self.inOffRange)
				else:
					self._rangeChangeDone = True
					return self.offHoursRanges.getTime2NextRange(now)
			else:
				self.logger.warning("Fail to switch all. We will try again on next loop.")
		return 0
