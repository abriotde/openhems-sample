#!/usr/bin/env python3
"""
This is the server thread witch aim to centralize information and take right deccisions
"""
import os
import time
from openhems.modules.energy_strategy import OffPeakStrategy, SwitchoffStrategy
from openhems.modules.network import HomeStateUpdaterException
from openhems.modules.util import CastUtililty
from openhems.modules.util.configuration_manager import ConfigurationManager, ConfigurationException


class OpenHEMSServer:
	"""
	This is the server thread witch aim to centralize information
	 and take right deccisions to optimize consumption
	"""

	def __init__(self, mylogger, network, serverConf:ConfigurationManager) -> None:
		self.logger = mylogger
		self.network = network
		self.loopDelay = serverConf.get("server.loopDelay")
		strategies = serverConf.get("server.strategies")
		self.strategies = []
		for strategyParams in strategies:
			strategy = strategyParams.get("class", "")
			strategyId = strategyParams.get("id", strategy)
			if strategy=="offpeak":
				self.strategies.append(OffPeakStrategy(mylogger, self.network, strategyId))
			elif strategy=="switchoff":
				offhoursrange = strategyParams.get('offrange', "[22h-6h]")
				reverse = CastUtililty.toTypeBool(strategyParams.get('reverse', False))
				self.strategies.append(SwitchoffStrategy(mylogger, self.network, strategyId, 
				                                         offhoursrange, reverse))
			elif strategy=="emhass":
				# pylint: disable=import-outside-toplevel
				# Avoid to import EmhassStrategy and all it's dependances when no needs.
				from openhems.modules.energy_strategy.emhass_strategy import EmhassStrategy
				self.strategies.append(EmhassStrategy(mylogger, self.network, serverConf, strategyId))
			else:
				self.logger.critical("OpenHEMSServer() : Unknown strategy '%s'", strategy)
				os._exit(1)

	def loop(self, loopDelay):
		"""
		It's the content of each loop.
		If loop delay=0, we consider that we never sleep (For test or reactivity).
		"""
		self.logger.debug("OpenHEMSServer.loop()")
		self.network.updateStates()
		for strategy in self.strategies:
				strategy.updateNetwork(loopDelay, True)

	def run(self, loopDelay=0):
		"""
		Run an infinite loop
		 where each loop shouldn't last more than loopDelay
		 and will never last less than loopDelay
		If loop delay=0, we consider that we never sleep (For test or reactivity).
		"""
		if loopDelay==0:
			loopDelay = self.loopDelay
		nextloop = time.time() + loopDelay
		while True:
			try:
				self.loop(loopDelay)
			except (HomeStateUpdaterException, ConfigurationException) as e:
				msg = ("Fail update network. Maybe Home-Assistant is down"
					" or long_lived_token expired. "+str(e))
				self.logger.error(msg)
			t = time.time()
			if t<nextloop:
				self.logger.debug("OpenHEMSServer.run() : sleep(%f min)", (nextloop-t)/60)
				time.sleep(nextloop-t)
				t = time.time()
			elif t>nextloop:
				self.logger.warning("OpenHomeEnergyManagement::run() "
					": missing time for loop : %d seconds", (nextloop-t))
			nextloop = t + loopDelay
