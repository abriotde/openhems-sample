"""
Super class for all EnergyStrategy modules
"""

import logging
# from openhems.modules.network.network import OpenHEMSNetwork
LOOP_DELAY_VIRTUAL = 0

class EnergyStrategy:
	"""
	Super class for all EnergyStrategy modules
	"""
	def  __init__(self, logger=None):
		if logger is None:
			logger = logging.getLogger(__name__)
		self.logger = logger

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
