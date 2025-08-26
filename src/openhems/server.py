#!/usr/bin/env python3
"""
This is the server thread witch aim to centralize information and take right deccisions
"""
import time
import datetime
import logging
from openhems.modules.energy_strategy import (
	OffPeakStrategy, SwitchoffStrategy, SimulatedAnnealingStrategy
)
from openhems.modules.network import HomeStateUpdaterException
from openhems.modules.util import (
	CastUtililty, ConfigurationManager, ConfigurationException, CastException
)
from openhems.modules.network import (
	FeedbackSwitch, ConstraintsException
)

class OpenHEMSServer:
	"""
	This is the server thread witch aim to centralize information
	 and take right deccisions to optimize consumption
	"""

	def __init__(self, mylogger, network, serverConf:ConfigurationManager, allowSleep=False) -> None:
		self.logger = mylogger
		self.network = network
		self.network.server = self
		self._loopDelay = serverConf.get("server.loopDelay")
		self.strategies = []
		self._cycleId = -1 # used for cache (if loopNb didn't move, get from cache)
		self._allowSleep = allowSleep
		self._inOverLoadMode = False # in over load mode, we have node deactivate for safety
		self._now = None # Current timestamp: Can be fake on simulation/tests mode.
		# "Nodes" to call decrementTime() to manage their time/constraints
		self.warningMessages = []
		self._decrementTimeCallbacks = {}
		self._initDecrementTimeCallbacks()
		self._initStrategies(mylogger, serverConf)

	def _initStrategies(self, mylogger, serverConf):
		"""
		Initialize the strategies.
		"""
		for strategyParams in serverConf.get("server.strategies"):
			strategy = strategyParams.get("class", "").lower()
			strategyId = strategyParams.get("id", strategy)
			throwErr = None
			try:
				if strategy=="offpeak":
					self.strategies.append(OffPeakStrategy(mylogger, self.network, strategyId))
				elif strategy=="switchoff":
					offhoursrange = strategyParams.get('offhours', "[22h-6h]")
					condition = strategyParams.get('condition', True)
					reverse = CastUtililty.toTypeBool(strategyParams.get('reverse', False))
					strategyObj = SwitchoffStrategy(mylogger, self.network, strategyId,
									offhoursrange, reverse=reverse, condition=condition)
					self.strategies.append(strategyObj)
				elif strategy=="emhass":
					# pylint: disable=import-outside-toplevel
					# Avoid to import EmhassStrategy and all it's dependances when no needs.
					from openhems.modules.energy_strategy.emhass_strategy import EmhassStrategy
					self.strategies.append(
						EmhassStrategy(mylogger, self.network, serverConf, strategyParams,
						strategyId=strategyId))
				elif strategy=="annealing":
					self.strategies.append(
							SimulatedAnnealingStrategy(
								mylogger, self.network, serverConf, strategyParams,
								strategyId=strategyId)
					)
				elif strategy in ["nosell", "nobuy", "ratiosellbuy"]:
					# Do not import SolarNoSellStrategy if not needed to avoid 'astral' depenency if not needed.
					from openhems.modules.energy_strategy.solarnosell_strategy import SolarNoSellStrategy
					self.strategies.append(
							SolarNoSellStrategy(
								mylogger, self.network, serverConf, strategyParams,
								strategyId=strategyId)
					)
				else:
					msg = f"OpenHEMSServer() : Unknown strategy '{strategy}'"
					self.logger.critical(msg)
					throwErr = msg
			except (ConfigurationException, CastException) as e:
				msg = f"Error initializing strategy '{strategyId}': {e.message}"
				throwErr = msg
			if throwErr is not None:
				self.logger.error(throwErr)
				self.warningMessages.append(throwErr)

	def getWarningMessages(self):
		return self.warningMessages + self.network.getWarningMessages()

	def _initDecrementTimeCallbacks(self):
		"""
		Initialize the decrement time callbacks with node we can't initialize before.
		"""
		for node in self.network.getAll("switch"):
			if isinstance(node, FeedbackSwitch):
				# We need to always check min/max sensor value
				self.registerDecrementTime(node)
			constraints = node.getConstraints()
			if constraints is not None:
				# We need to always check specific contraints like min/maxPower, maxDurationOn/Off
				self.registerDecrementTime(constraints)


	def getSchedule(self):
		"""
		Return scheduled planning.
		"""
		schedule = {}
		for strategy in self.strategies:
			nodes = strategy.getSchedulableNodes()
			for node in nodes:
				myid = node.id
				sc = node.getSchedule()
				if sc is not None:
					schedule[myid] = sc
		return schedule

	def registerDecrementTime(self, node, register:bool=True):
		"""
		Register a node witch will decrement time.
		"""
		if register:
			self.logger.debug("Register decrement time for node '%s'", node)
			self._decrementTimeCallbacks[id(node)] = node
		else:
			self.logger.debug("Unregister decrement time for node '%s'", node)
			self._decrementTimeCallbacks.pop(id(node))

	def getTime(self):
		"""
		Return current time
		"""
		return self._now

	def getCycleId(self):
		"""
		Return cycle id.
		"""
		return self._cycleId

	def decrementTime(self, duration):
		"""
		Decrement time from all objects neither the type (Thanks Python ;) )
		"""
		self.logger.debug("decrementTime(%s)", duration)
		for node in self._decrementTimeCallbacks.values():
			self.logger.debug(" - for '%s'", node)
			try:
				node.decrementTime(duration)
			except ConstraintsException as e:
				self.logger.error("Constraint error : %s", e.message)
				if self.logger.isEnabledFor(logging.DEBUG):
					self.logger.exception(e)
				self.network.notify(
					f"Constraint error: {e.message}"
				)

	def _disableDevicesDue2OverLoad(self,marginPowerOn):
		"""
		Disable devices due to over-load.
		This is called by the network when margin power is negative.
		"""
		elems = self.network.getAll("switch")
		elems.sort( # start from the less priority
			key=lambda x:x.getPriority()
		)
		for elem in elems:
			if marginPowerOn<0 and elem.isSwitchable() and elem.isOn():
				power = elem.getCurrentPower()
				self.logger.info("Switch off '%s' due to missing power margin.", elem.id)
				if elem.switchOn(False):
					self.logger.error("DevicesDue2OverLoad: Fail switch off '%s'.", elem.id)
				else:
					marginPowerOn += power
					elem.setActivate(False)
					self._inOverLoadMode = True

	def check(self):
		""""
		For safety, Avoid over-load, check margin power.
		If margin power is used, we switch off devices
		"""
		marginPowerOn = self.network.getMarginPowerOn()
		self.logger.debug("Security margin power:%s",marginPowerOn)
		if marginPowerOn<0: # Need to switch off (deactivate) some nodes
			self.logger.warning(
				"Margin power On is negativ (%f): Need to sitch off devices.",
				marginPowerOn)
			self._disableDevicesDue2OverLoad(marginPowerOn)
		elif self._inOverLoadMode and marginPowerOn>0: # Try to re-activate nodes
			inOverLoadMode = False
			# start from the bigest priority (default order)
			elems = self.network.getAll("switch")
			for elem in elems:
				if not elem.isActivate():
					if elem.getMaxPower()>marginPowerOn: # re-activate the node
						elem.setActivate(True)
						# Do just one at each loop for safety
						return marginPowerOn
					inOverLoadMode = True
			self._inOverLoadMode = inOverLoadMode
		return marginPowerOn


	def loop(self, now=None):
		"""
		It's the content of each loop.
		If loop delay=0, we consider that we never sleep (For test or reactivity).
		"""
		if now is None:
			now = datetime.datetime.now()
		if self._now is None:
			loopDelay = 0
		else:
			loopDelay = now - self._now
			loopDelay = loopDelay.total_seconds()
		self._cycleId += 1
		self._now = now
		# self.logger.debug("OpenHEMSServer.loop(%s)", now)
		self.network.updateStates()
		self.check()
		self.decrementTime(loopDelay)
		time2wait = 86400
		for strategy in self.strategies:
			t = strategy.updateNetwork(loopDelay, now)
			time2wait = min(t, time2wait)
		if self._allowSleep and time2wait > 0:
			self.logger.info("Loop sleep(%d min)", round(time2wait/60))
			time.sleep(time2wait)

	def run(self, loopDelay=0):
		"""
		Run an infinite loop
		 where each loop shouldn't last more than loopDelay
		 and will never last less than loopDelay
		If loop delay=0, we consider that we never sleep (For test or reactivity).
		"""
		if loopDelay==0:
			loopDelay = self._loopDelay
		nextloop = time.time() + loopDelay
		while True:
			# pylint: disable=broad-exception-caught
			# self.network.notify("OpenHEMS is running")
			try:
				self.loop()
			except HomeStateUpdaterException as e:
				# at least HomeStateUpdaterException, CastException, HomeStateUpdaterException
				self.logger.error("Fail update network : %s", e)
				if self.logger.isEnabledFor(logging.DEBUG):
					self.logger.exception(e)
				if e.code == CastException.UNAVAILABLE:
					self.network.notify(
						"Could you solve that problem? It seam we can't get information from "
						+ e.message
					)
				self.network.notify("Fail update network : "+e.message)
			except ConstraintsException as e:
				self.logger.error("Constraint error : %s", e.message)
				if self.logger.isEnabledFor(logging.DEBUG):
					self.logger.exception(e)
				self.network.notify(
					f"Constraint error : {e.message}"
				)
			except Exception as e:
				self.logger.error("Fail update network : %s", str(e))
				if self.logger.isEnabledFor(logging.DEBUG):
					self.logger.exception(e)
			t = time.time()
			if t<nextloop:
				self.logger.debug("OpenHEMSServer.run() : sleep(%.2f min)", (nextloop-t)/60)
				time.sleep(nextloop-t)
				t = time.time()
			elif t>nextloop:
				self.logger.warning("OpenHomeEnergyManagement::run() "
					": missing time for loop : %d seconds", (nextloop-t))
			nextloop = t + loopDelay
