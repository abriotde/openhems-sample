"""
Super class for all EnergyStrategy modules

List of todo list to integrate a strategy
- Implemented : Implement main functions inherit from EnergyStrategy:
   at least __init__() and updateNetwork() (or eval and apply)
- Call : Call constructor in server.py
- Conf : Configure it in openhems_default.py
- TestAuto : Add unittest in test_xxx_strategy.py.
- RunOk : Unitest do not test all, if run ok, all seam really ok.
- InProd : If it's tested in a real house.

#DONE: Implemented - Call - Conf - TestAuto - RunOk - InProd
"""

import logging
import datetime
from openhems.modules.network.network import OpenHEMSNetwork

LOOP_DELAY_VIRTUAL = 0

class StrategyNode:
	"""
	Class to manage a node in a strategy: keep track of its state
	"""
	def  __init__(self, node, logger):
		self.logger = logger
		self.node = node
		self.isOn = None

	def changed(self, isOn=None):
		"""
		Change the state of the node
		"""
		wasOn = self.isOn
		if isOn is None:
			isOn = self.node.isOn()
		self.isOn = isOn
		return wasOn!=self.isOn

	def decreaseTime(self, cycleDuration:int):
		"""
		Decrease the time of the schedule
		"""
		if self.isOn:
			if not self.node.isOn(): # Was successfully switched off at previous cycle
				self.isOn = False
				return False
			schedule = self.node.getSchedule()
			remainingTime = schedule.decreaseTime(cycleDuration)
			if remainingTime==0:
				self.logger.info("Switch off '%s' due to elapsed time.", self.node.id)
				if self.node.switchOn(False):
					self.logger.warning("Fail switch off '%s'.", self.node.id)
				else:
					return False
			return True
		return False

class DefaultDeferrable:
	"""
	Class to manage a deferrable device
	"""
	def __init__(self, node, durationInSecs:int):
		self.node = node
		self.durationInSecs = durationInSecs

	def getDuration(self):
		"""
		return the duration of the deferrable device
		"""
		return self.durationInSecs

	def setDuration(self, durationInSecs:int):
		"""
		Set the duration of the deferrable device
		"""
		self.durationInSecs = durationInSecs

class EnergyStrategy:
	"""
	Super class for all EnergyStrategy modules
	"""
	def  __init__(self, strategyId:str, network:OpenHEMSNetwork,
	              logger=None, evalFrequency:int=60):
		if logger is None:
			logger = logging.getLogger(__name__)
		self.logger = logger
		self.strategyId = strategyId
		self.network = network
		self._nodes = None
		self.evalFrequence = datetime.timedelta(minutes=evalFrequency)
		self.nextEvalDate = datetime.datetime.now() - self.evalFrequence
		self.deferables = {}
		self.deferablesKeys = []

	def getNodes(self, encapsulated=False):
		"""
		Return nodes concerned by a defined strategy
		"""
		if encapsulated:
			if self._nodes is None:
				self._nodes = [
					StrategyNode(node, self.logger)
					for node in self.network.getNodesForStrategy(self.strategyId)
				]
			return self._nodes
		return self.network.getNodesForStrategy(self.strategyId)

	def _switchSchedulableWitchIsOff(self, node, cycleDuration, doSwitchOn):
		"""
		Like switchSchedulable() but for node off and switchable
		"""
		del cycleDuration
		if doSwitchOn and node.getSchedule().duration>0:
			marginPower = node.network.getMarginPowerOn()
			if node.getMaxPower()>marginPower:
				self.logger.info(
					"Not enough power margin (%d) to switch on '%s' witch need %d Kw.",
					marginPower, node.id, node.getMaxPower())
				return False
			if not node.isActivate():
				self.logger.info(
					"Can't switch on '%s' due to deactivation for margin power security.",
					node.id)
				return False
			if node.switchOn(True):
				self.logger.info("Switch on '%s' successfully.", node.id)
				return True
			self.logger.warning("Fail switch on '%s'.", node.id)
		else:
			self.logger.debug("Node '%s' is off.",
				node.id)
		return False

	def switchSchedulable(self, node, cycleDuration, doSwitchOn):
		"""
		param node: Node to switch on
		param doSwitchOn: Set if we want to switch on or off
		return: True if node is on
		"""
		if node.isSwitchable:
			if node.isOn():
				remainingTime = node.getSchedule().decreaseTime(cycleDuration)
				if remainingTime==0 or not doSwitchOn:
					self.logger.info("Switch off '%s' due to %s.",
						node.id, "elapsed time" if remainingTime==0 else "strategy")
					if node.switchOn(False):
						self.logger.warning("Fail switch off '%s'.", node.id)
						return True
				else:
					self.logger.debug("Node %s isOn for %s more seconds", \
						node.id, remainingTime)
					return True
			else:
				return self._switchSchedulableWitchIsOff(node, cycleDuration, doSwitchOn)
		else:
			self.logger.debug("switchOn() : Node is not switchable : %s.", node.id)
		return False

	def switchOffAll(self, cycleDuration=1):
		"""
		Switch of all connected devices with this strategy.
		"""
		self.logger.debug("EnergyStrategy.switchOffAll(%s)", self.strategyId)
		ok = True
		for elem in self.getNodes():
			# self.logger.debug("Switch off '%s'", elem.id)
			if elem.isSwitchable and self.switchSchedulable(elem, cycleDuration, False):
				self.logger.warning("Fail to switch off '%s'",elem.id)
				ok = False
		return ok

	def getSchedulableNodes(self):
		"""
		Return the list of nodes that should be scheduled by the user, using the HTTP UI
		 to start (or stop) the device
		"""
		return self.getNodes()

	def getDeferrable(self, node, durationInSecs:int):
		"""
		return: a Deferable device witch can be encapsulated if usefull
		This function can be overload.
		"""
		return DefaultDeferrable(node, durationInSecs)

	def updateDeferables(self):
		"""
		Update scheduled devices according to emhass
		 to scheduled devices according to openhems
		Return true if schedule has been updated
		"""
		# self.logger.debug("EnergyStrategy.updateDeferables()")
		update = False
		self.deferables = {}
		for node in self.getNodes():
			nodeId = node.id
			durationInSecs = node.getSchedule().duration
			deferable = self.deferables.get(nodeId, None)
			if deferable is None:
				if durationInSecs>0: # Add a new deferrable
					update = True
					self.deferables[nodeId] = self.getDeferrable(node, durationInSecs)
			else:
				if durationInSecs<=0: # Remove a deferrable
					del self.deferables[nodeId]
					update = True
				elif deferable.getDuration()!=durationInSecs: # update a deferrable
					update = True
					deferable.setDuration(durationInSecs)
		self.logger.debug("EnergyStrategy.updateDeferables() => %s : %s", update, self.deferables)
		return update

	def check(self, now=None):
		"""
		Check and eval if necessary
		- EMHASS optimization
		- power margin
		- conformity to EMHASS plan
		"""
		# self.logger.debug("EnergyStrategy.check()")
		if now is None:
			now = datetime.datetime.now()
		if self.updateDeferables() or now>self.nextEvalDate:
			# self.logger.debug("EnergyStrategy.check() : eval")
			self.eval()
			self.nextEvalDate = datetime.datetime.now() + self.evalFrequence

	def eval(self):
		"""
		This function must be overload
		"""
		self.logger.debug("EnergyStrategy.eval() must be overload")

	def apply(self, cycleDuration, now):
		"""
		This function must be overload
		"""
		del cycleDuration, now
		self.logger.debug("EnergyStrategy.apply() must be overload")

	def updateNetwork(self, cycleDuration, now=None):
		"""
		Generic function to updateNetwork base on algorythm
		In that case, sub-strategy must implement :
		- eval()
		- apply(cycleDuration, now)
		"""
		if now is None:
			now = datetime.datetime.now()
		self.check(now)
		self.apply(cycleDuration, now=now)
		return cycleDuration


	def switchOnMax(self, cycleDuration):
		"""
		Switch on nodes, but 
		 - If there is no margin to switch on, do nothing.
		 - Only one (To be sure to not switch on to much devices)
		"""
		self.logger.info("%s.switchOnMax()", self.strategyId)
		marginPower = self.network.getMarginPowerOn()
		if marginPower<=0:
			self.logger.info("Can't switch on devices: not enough power margin : %s", marginPower)
			return True
		for elem in self.getNodes(True):
			switchOn = self.switchSchedulable(elem.node, cycleDuration, True)
			if switchOn and elem.changed(switchOn):
				self.logger.info("Switch on just one device at each loop to ensure Network constraint.")
				return True
		return False
