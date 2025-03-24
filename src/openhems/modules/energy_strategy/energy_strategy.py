"""
Super class for all EnergyStrategy modules
"""

import logging
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
		else:
			return False
	

class EnergyStrategy:
	"""
	Super class for all EnergyStrategy modules
	"""
	def  __init__(self, strategyId:str, network:OpenHEMSNetwork,
	              logger=None, useSchedulable:bool=False):
		if logger is None:
			logger = logging.getLogger(__name__)
		self.logger = logger
		self.strategyId = strategyId
		self.network = network
		self.useSchedulable = useSchedulable
		self._nodes = None

	def getNodes(self, encapsulated=False):
		"""
		Return nodes concerned by a defined strategy
		"""
		if encapsulated:
			if self._nodes is None:
				self._nodes = [StrategyNode(node, self.logger) for node in self.network.getNodesForStrategy(self.strategyId)]
			return self._nodes
		return self.network.getNodesForStrategy(self.strategyId)

	def updateNetwork(self, cycleDuration:int, allowSleep:bool, now=None):
		"""
		Function to update OpenHEMSNetwork. To implement in sub-class
		"""
		del cycleDuration, allowSleep, now
		self.logger.error("EnergyStrategy.updateNetwork() : To implement in sub-class")

	def switchOnSchedulable(self, node, cycleDuration, doSwitchOn):
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

	def switchOffAll(self):
		"""
		Switch of all connected devices with this strategy.
		"""
		# self.print(logger.info)
		# marginPower = self.getCurrentPowerConsumption()
		# self.print(logger.info)
		ok = True
		for elem in self.getNodes():
			if elem.isSwitchable and elem.switchOn(False):
				self.logger.warning("Fail to switch off '%s'",elem.id)
				ok = False
		return ok

	def getSchedulableNodes(self):
		"""
		Return the list of nodes that should be scheduled by the user, using the HTTP UI
		 to start (or stop) the device
		"""
		if not self.useSchedulable:
			return []
		return self.getNodes()
