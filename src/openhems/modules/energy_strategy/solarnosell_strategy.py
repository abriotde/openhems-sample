"""
It's the simplest use case to manage solar-electricity.
Usefull for fixed public grid price (No offpeak prices).
Case offpeak + solar-panel, use emhass or simulated annealing strategy

#TODO : TestAuto - RunOk - InProd : 3/6
"""
from openhems.modules.network.network import Network
from openhems.modules.util import ConfigurationManager
from .solarbased_strategy import SolarBasedStrategy

class SolarNoSellStrategy(SolarBasedStrategy):
	"""Could be named too NoBuy
	* Start the device when production > consommation + X * consommationDevice (during Y cycles?)
	* Stop a device if production < consommation - (1-X) * consommationDevice (during Y cycles?)
	If X==0 we could never sell electricity
	(If there is enough device consumption and the cycle duration is enough quick).
	If X==1 we could never buy electricity
	(If produce enough and the cycle duration is enough quick).
	But with a margin every thing get harder because we want "+ margin" for no-sell
	and "- margin" for no-buy.
	We found a solution using "- ratio*margin" and ratio between on interval [-1 ; 1]
	Problem is that precedent solutions do not whork with X = -1, So X = - (((ratio-1)²-4)/4)
	then even if ratio is in [-1 ; 1] X stay in [0 ; 1]
	* Ratio = -1, production<consumption : no sell
	* Ratio = 1, consumption<production : no buy
	The good news is that for 0 it's something between, and even for 2 or -2.
	"""

	def __init__(self, mylogger, network: Network,
			configurationGlobal:ConfigurationManager, configurationStrategy:dict,
			*, strategyId:str="nosell"):
		super().__init__(strategyId, network, configurationGlobal, mylogger)
		self._ratio = configurationStrategy.get("ratio")
		self._margin = configurationStrategy.get("margin")
		self._cycleDuration = configurationStrategy.get("cycleDuration")
		self._refCoefficient = configurationStrategy.get("refCoefficient")
		self.logger.info("SolarNoSellStrategy()")
		self._cycleNb = 0 # determine the number of cycles.
		# If cycleNb == +X, coef was positive during last X cycles
		# If cycleNb == -X, coef was negative during last X cycles
		self._coefs = [] # List of last cycleNb coefs

	def check(self, now=None):
		"""
		Nothing todo
		"""
		del now

	def switchOnDevices(self, powerMargin):
		"""
		Switch on devices if production > consommation + X * consommationDevice
		Can switch on many devices if there is enought power powerMargin
		"""
		assert powerMargin>self._margin
		for node in self.getNodes():
			if node.isOn():
				continue
			# production > consommation + X * consommationDevice - powerMargin
			#  = (production - consommation) > X * consommationDevice
			#  = powerMargin  > X * consommationDevice
			# powerMargin+(((ratio-1)²-4)/4)*consommationDevice-ratio*margin>0
			coef = powerMargin+((pow(self._ratio-1, 2)-4)/4)*node.getMaxPower() \
				-self._ratio*self._margin
			if coef<=0:
				continue
			self._cycleNb = self._cycleNb+1 if self._cycleNb>=0 else 1
			c = self._cycleNb
			self._coefs[c-1] = coef
			self.logger.info("SolarNoSellStrategy: coef+=%s", coef)
			if (c>=self._cycleDuration
					or sum(self._coefs[slice(0,c)])>self._refCoefficient):
				if self.switchSchedulable(node, True):
					powerMargin -= node.getMaxPower()
					if powerMargin<=0:
						return True
		return False

	def switchOffDevices(self, powerMargin):
		"""
		Switch off devices if production < consommation - (1-X) * consommationDevice
		Can switch off many devices if there is enought power powerMargin
		"""
		assert powerMargin<self._margin
		# Reverse because begin to switch off nodes with lowest priority
		for node in reversed(self.getNodes()):
			if not node.isOn():
				continue
			# production < consommation - (1-X) * consommationDevice
			#  = (production - consommation) < (X-1) * consommationDevice
			# Solution with coef between -1 and 1 : X = - (((ratio-1)²-4)/4)
			# powerMargin+(1+(((ratio-1)²-4)/4))*consommationDevice-ratio*margin<0
			coef = powerMargin+(1+((pow(self._ratio-1, 2)-4)/4))*node.getCurrentPower() \
				-self._ratio*self._margin
			if coef>=0:
				continue
			self._cycleNb = self._cycleNb-1 if self._cycleNb<=0 else -1
			c = -1*self._cycleNb
			self._coefs[c-1] = coef
			self.logger.info("SolarNoSellStrategy: coef-=%s", coef)
			if (c>=self._cycleDuration
					or sum(self._coefs[slice(0,c)])>self._refCoefficient):
				if self.switchSchedulable(node, False):
					powerMargin += node.getMaxPower()
					if powerMargin>=0:
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
		del now
		self.logger.debug("SolarNoSellStrategy.apply()")
		consumption = self.network.getCurrentPower()
		consumptionBattery = self.network.getCurrentPower("battery")
		productionSolarPanel = self.network.getCurrentPower("solarpanel")
		powerMargin = productionSolarPanel - consumption + consumptionBattery
		if powerMargin>self._margin:
			if self.switchOnDevices(powerMargin):
				return max(cycleDuration/5, 3)
		elif powerMargin<self._margin:
			if self.switchOffDevices(powerMargin):
				return max(cycleDuration/5, 3)
		# TODO : Return short timeout if we switch on a device,
		#  to quicly react if it's not enough (or too much)
		#  (more chances are the state will evolv after).
		return cycleDuration
