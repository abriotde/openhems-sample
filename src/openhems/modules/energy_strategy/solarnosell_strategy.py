"""
It's the simplest use case to manage solar-electricity. Usefull for fixed public grid price (No offpeak prices).
Case offpeak + solar-panel, use emhass or simulated annealing strategy

#TODO : TestAuto - RunOk - InProd : 3/6
"""
import datetime
import logging
from openhems.modules.network.network import OpenHEMSNetwork
from openhems.modules.util import ConfigurationManager
from .solarbased_strategy import SolarBasedStrategy, GeoPosition

class SolarNoSellStrategy(SolarBasedStrategy):
	"""
	Could be named too NoBuy
	- Start the device when production > consommation + X * consommationDevice (during Y minutes?)
	- Stop a device if production < consommation - (1-X) * consommationDevice (during Y minutes?)
	If X==0 we could never sell electricity (If there is enough device consumption and the cycle duration is enough quick).
	If X==1 we could never buy electricity (If produce enough and the cycle duration is enough quick).
	"""
	def __init__(self, mylogger, network: OpenHEMSNetwork,
			configurationGlobal:ConfigurationManager, configurationStrategy:dict,
			strategyId:str="nosell"):
		del configurationGlobal
		super().__init__(strategyId, network, configurationGlobal, mylogger)
		self._ratio = configurationStrategy.get("ratio")
		self.logger.info("SolarNoSellStrategy()")

	def check(self, now=None):
		"""
		Nothing todo
		"""

	def switchOnDevices(self, cycleDuration, margin):
		"""
		Switch on devices if production > consommation + X * consommationDevice
		Can switch on many devices if there is enought power margin
		"""
		assert margin>0
		for node in self.getNodes():
			if not node.isOn():
				# production > consommation + X * consommationDevice
				#  = (production - consommation) > X * consommationDevice
				#  = margin  > X * consommationDevice
				if (self._ratio==0
						or margin>self._ratio*node.getMaxPower()):
					if self.switchSchedulable(node, cycleDuration, True):
						margin -= node.getMaxPower()
						if margin<=0:
							return True
		return False

	def switchOffDevices(self, cycleDuration, margin):
		"""
		Switch off devices if production < consommation - (1-X) * consommationDevice
		Can switch off many devices if there is enought power margin
		"""
		assert margin<0
		# Reverse because begin to switch off nodes with lowest priority
		for node in reversed(self.getNodes()): 
			if node.isOn():
				# production < consommation - (1-X) * consommationDevice
				#  = (production - consommation) < (X-1) * consommationDevice
				if (self._ratio==0
						or margin<(self._ratio-1)*node.getCurrentPower()):
					if self.switchSchedulable(node, cycleDuration, False):
						margin += node.getMaxPower()
						if margin>=0:
							return True
		return False

	def apply(self, cycleDuration, now):
		"""
		Called on each loop to switch on/off devices.
		Switch on devices if production > consommation + X * consommationDevice
		Switch off devices if production < consommation - (1-X) * consommationDevice
		Chances are we avoid ping-pong effect because when start device, we use max power,*
		  but usually the real power is lower, and it's this we use to switch off
		"""
		del cycleDuration, now
		self.logger.debug("SolarNoSellStrategy.apply()")
		consumption = self.network.getCurrentPower()
		consumptionBattery = self.network.getCurrentPower("battery")
		productionSolarPanel = self.network.getCurrentPower("solarpanel")
		margin = productionSolarPanel - consumption + consumptionBattery
		if margin>0:
			if self.switchOnDevices(cycleDuration, margin):
				return max(cycleDuration/10, 3)
		elif margin<0:
			if self.switchOffDevices(cycleDuration, margin):
				return max(cycleDuration/10, 3)
		# TODO : Return short timeout if we switch on a device,
		#  to quicly react if it's not enough (or too much)
		#  (more chances are the state will evolv after).
		return cycleDuration