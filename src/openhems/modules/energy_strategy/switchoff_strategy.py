"""
This is in case we just base on "off-peak" range hours to control output.
	 Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours

#TODO : TestAuto - RunOk - InProd : 3/6
"""
from datetime import datetime
from openhems.modules.network.network import OpenHEMSNetwork
from openhems.modules.util import ConfigurationException, HoursRanges
from .energy_strategy import EnergyStrategy


# pylint: disable=broad-exception-raised
class SwitchoffStrategy(EnergyStrategy):
	"""
	This is in case we just want to switch on a device at a time,
	 and switch off it at an other time
	(Like internet box for WiFi, or swimming-pool pump, or controlled mechanical ventilation).
	"""

	def __init__(self, mylogger, network: OpenHEMSNetwork, strategyId:str,
		     offHoursRanges, reverse=False, condition=True):
		super().__init__(strategyId, network, mylogger)
		self.offHoursRanges = HoursRanges(offHoursRanges)
		self.inOffRange = False
		self._rangeEnd = datetime.now()
		self._rangeChangeDone = False
		self._todo = self.getNodes()
		self._backupStates = {}
		self.reverse = reverse
		self.condition = condition # Optional additional condition to enter switoff period
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
		self.inOffRange, self._rangeEnd, _ = self.offHoursRanges.checkRange(nowDatetime)
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
				self.logger.info("Switch %s '%s' successfully", switchStr, node.id)
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
		isPeriodStart = (not switchOn) ^ self.reverse # Start of period : remember states
		if isPeriodStart and not self.testCondition(): # Cancel if condition is not satisfied
			return True
		for elem in self._todo:
			msg = ""
			if isPeriodStart: # Start of period : remember states
				isOn = elem.isOn()
				self._backupStates[elem.id] = isOn
				if isOn==switchOn:
					_switchOn = None
					msg = "Start of period : Node is ever "+("on" if switchOn else "off")
				else:
					_switchOn = switchOn
			else: # End of period : restore states
				_switchOn = self._backupStates.get(elem.id, None)
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

	def updateNetwork(self, cycleDuration:int, now=None) -> int:
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
			if self.switchOnAll(not self.inOffRange ^ self.reverse):
				self._rangeChangeDone = True
				return self.offHoursRanges.getTime2NextRange(now)
			self.logger.warning("Fail to switch all. We will try again on next loop.")
		return 0

	def getVal(self, key:str):
		"""
		Function for eval in self.testCondition to get Home-Assistant entity value.
		"""
		self.logger.debug("SwitchOffStrategy.getVal(%s)",key)
		val = self.network.networkUpdater.getValue(key)
		self.logger.debug("SwitchOffStrategy.getVal(%s) = %s", key, val)
		return val

	def testCondition(self):
		"""
		Test optional additional condition to enter switoff period.
		It use Python eval. It should be better to use more secure
		 (And portable standard) way like 
		 * Lua language but it will need to reimplement Home-Assistant API call
		  ( + Parsing YAML files to get token)
		 * Restricted Python function : https://stackoverflow.com/questions/3513292/python-make-eval-safe.
		"""
		if not isinstance(self.condition, str):
			return True
		# env = {
		# 	"locals": locals(),
		# 	"globals" : None,
		# 	"__name__" :  None,
		# 	"__file__" :  None,
		# 	"__builtins__" :  None
		# }
		# print(locals())
		# pylint: disable=eval-used
		try:
			a = eval(self.condition) # , env)
		except NameError as e:
			self.logger.error("testCondition(%s) = ERROR : %s : Ignore this condition.",
			                  self.condition, str(e))
			return True
		self.logger.debug("SwitchOffStrategy.testCondition(%s) = %s", self.condition, a)
		if not isinstance(a, bool):
			raise ConfigurationException(f"SwitchoffCondition is not valid : not boolean : {self.condition}")
		return a
