"""
This module aim to abstract home network of connected devices.
It is used to know devices and to switch on/off them.
"""

from typing import Final
import copy
from openhems.modules.util.notification_manager import NotificationManager
from .node import Node
from .outnode import OutNode, Switch
from .inoutnode import (
	InOutNode, PublicPowerGrid, SolarPanel, Battery
)
from .homestate_updater import HomeStateUpdater

POWER_MARGIN: Final[int] = 10 # Margin of power consumption for security

# pylint: disable=too-many-public-methods
class Network:
	"""
	This class aim to abstract home network of connected devices.
	It is used to know devices and to switch on/off them.
	"""
	def print(self, printer=None):
		"""
		Print Network as human readable string
		"""
		if printer is None:
			printer = print
		printer("Network(")
		printer(" IN : ")
		for elem in self.getAll("inout"):
			printer("  - "+str(elem))
		printer(" OUT : ")
		for elem in self.getAll("out"):
			printer("  - "+str(elem))
		printer(")")

	def __init__(self, logger, networkUpdater, nodesConf, server=None):
		self.networkUpdater: HomeStateUpdater = None
		self.nodes = []
		self.notificationManager = None
		self._filteredNodesCache = {} # List of nodes by categories
		self.logger = logger
		self._loopNb = 0 # used for cache (if loopNb didn't move, get from cache)
		self._loopNbMarginPowerOn = -1
		self._marginPowerOn = -1
		self.server = server
		self.addNetworkUpdater(networkUpdater, nodesConf)

	def getCycleId(self):
		"""
		Return the refresh Id of the network.
		"""
		if self.server is None:
			return -1
		return self.server.getCycleId()

	def addNetworkUpdater(self, networkUpdater: HomeStateUpdater, nodesConf):
		"""
		Add a networkUpdater (HomeStateUpdater) with is required.
		"""
		# print("addNetworkUpdater()")
		networkUpdater.initNetwork(self)
		self.networkUpdater = networkUpdater
		networkUpdater.getNodes(nodesConf)
		self.notificationManager = NotificationManager(self.networkUpdater)
		self.print(self.logger.info)

	def getWarningMessages(self):
		"""
		Return a list of important problems during initializing Network.
		"""
		return self.networkUpdater.warningMessages

	def getSchedule(self):
		"""
		Return scheduled planning.
		"""
		schedule = {}
		for node in self.getAll("out"):
			myid = node.id
			sc = node.getSchedule()
			schedule[myid] = sc
		return schedule

	def addNode(self, elem: Node) -> Node:
		"""
		Add a node.
		"""
		elem.network = self
		self.nodes.append(elem)
		self._filteredNodesCache = {}
		return elem

	def getCurrentPower(self, filterId="inout"):
		"""
		Get current power consumption by all network.
		"""
		globalPower = 0
		for elem in self.getAll(filterId):
			globalPower += elem.getCurrentPower()
		return globalPower

	def _getAll(self, filterId, elemFilter=None):
		"""
		Return Out nodes, filtered by strategy=strategyId if set.
		!!! WARNING !!! filterId and elemFilter must be bijectiv (one-to-one)
		"""
		out = self._filteredNodesCache.get(filterId, None)
		if out is None:
			if elemFilter is None:
				filters = {
					"inout" : (lambda x: isinstance(x, InOutNode)),
					"out" : (lambda x: isinstance(x, OutNode)),
					"switch" : (lambda x: isinstance(x, Switch)),
					"publicpowergrid" : (lambda x: isinstance(x, PublicPowerGrid)),
					"battery" : (lambda x: isinstance(x, Battery)),
					"solarpanel" : (lambda x: isinstance(x, SolarPanel)),
				}
				elemFilter = filters.get(filterId, None)
			if elemFilter is not None:
				out = list(filter(elemFilter, self.nodes))
				if filterId=="switch":
					out.sort(
						reverse=True, key=lambda x:x.getPriority()
					)
			elif filterId=="":
				out = self.nodes
			else:
				self.logger.error("Network.getAll() : unknown filterId '%s'",
					 filterId)
				out = None
			self._filteredNodesCache[filterId] = out
		return out

	def getAll(self, filterId):
		"""
		Same as private _getAll() except that we can't set custom elemFilter
		 to avoid incoherence between elemFilter AND filterId
		"""
		return self._getAll(filterId)

	def _sumNodesValues(self, filterId, defaultFilter, function):
		"""
		Sum all values from nodes (filtered by filterId).
		"""
		if filterId is None:
			filterId = defaultFilter
		globalPower= 0
		for elem in self._getAll(filterId):
			globalPower += function(elem)
		return globalPower

	def getMaxPowerProduction(self, filterId=None):
		"""
		Get current maximum power consumption possible.
		It's instant max-power
		- For solar panel, max-power = current-power.
		- For public power grid, it's usually a constant.
		"""
		return self._sumNodesValues(filterId, "inout", (lambda x: x.getMaxPower()))

	def getMaxPowerConsumption(self):
		"""
		Return how much the network could consume if all devices switched on consume at there max.
		But we don't have all real nodes we must
		- Add global power consumption
		- Add nodes maxPower and substract there currentPower (count in global power)
		"""
		globalPower = self.getCurrentPower()
		for elem in self.getAll("out"):
			if elem.isOn():
				globalPower += elem.getMaxPower() - elem.getCurrentPower()
		return globalPower

	def getMinPower(self, filterId=None):
		"""
		Get current minimum power consumption possible.
		0 mean, we can't give back power to network grid.
		"""
		return self._sumNodesValues(filterId, "inout", (lambda x: x.getMinPower()))

	def getMarginPower(self, filterId=None):
		"""
		Return margin power
		(Power to keep before considering extrem value)
		"""
		if filterId is None:
			filterId = "inout"
		vals = [x.getMarginPower() for x in self.getAll(filterId)]
		return max(vals)

	def getMarginPowerOn(self):
		"""
		Get how many power we can add safely
		"""
		if self._loopNbMarginPowerOn != self._loopNb:
			# The maximum production before black-out
			maxPowerP = self.getMaxPowerProduction()
			# The consumption if every switched on devices consume at max capability
			currentPower = self.getCurrentPower()
			maxPowerC = self.getMaxPowerConsumption()
			marginPower = self.getMarginPower()
			marginA = maxPowerP-(currentPower+marginPower)
			marginB = maxPowerP-maxPowerC # Maybe is it too safe?
			self._marginPowerOn = min(marginA, marginB)
			self._loopNbMarginPowerOn = self._loopNb
		return self._marginPowerOn

	def getMarginPowerOff(self):
		"""
		Get how many power we can remove safely (Case we do not want to over produce)
		"""
		minPower = self.getMinPower()
		currentPower = self.getCurrentPower()
		marginPower = self.getMarginPower()
		marginPowerOff = (currentPower-marginPower)-minPower
		if marginPowerOff<0: # Need to switch on some elements
			while marginPowerOff<0:
				for elem in self.getAll("out"):
					if elem.isSwitchable() and not elem.isOn():
						if elem.switchOn(True):
							marginPowerOff += elem.maxPower
							# Not safe, should we use minPower or avgPower... TODO?
			return 0
		return marginPowerOff

	def notify(self, message:str):
		"""
		Send a notification using the appropriate way 
		(Only push to HomeAssistant for the moment).
		"""
		self.logger.info("Network.notify(%s)", message)
		self.notificationManager.notify(message)

	def switchOffAll(self):
		"""
		Switch of all connected devices.
		"""
		self.logger.info("Network.switchOffAll()")
		# self.print(logger.info)
		# marginPower = self.getCurrentPower()
		# self.print(logger.info)
		ok = True
		for elem in self.getAll("out"):
			if elem.isSwitchable() and elem.switchOn(False):
				self.logger.warning("Fail to switch off '%s'",elem.id)
				ok = False
		return ok

	def updateStates(self):
		"""
		Update network state using the NetworkUpdater
		"""
		self._loopNb += 1
		self.networkUpdater.updateNetwork()

	def isGridSourceOn(self):
		"""
		Return true if grid source is available (even if no power is used)
		"""
		return self.getAll("publicpowergrid") != []

	def getBattery(self) -> Battery:
		"""
		Return a battery representing the sum of all battery.
		"""
		batteries = self.getAll("battery")
		l = len(batteries)
		if l<1:
			return Battery("fakeBattery", 0, 0)
		if l==1:
			return batteries[0]
		# TODO
		bat = copy.copy(batteries[0])
		bat.setId(batteries[0].id + "_sum")
		return bat

	def getNodesForStrategy(self, strategyId):
		"""
		Return list of nodes for a strategy
		"""
		# self.logger.debug("getNodesForStrategy(%s)", strategyId)
		key = "strategy_"+strategyId
		nodes = self._filteredNodesCache.get(key, None)
		if nodes is None:
			# self.logger.debug("getNodesForStrategy() : generate cache")
			nodes = []
			for node in self.getAll("switch"):
				strategy = node.getStrategyId()
				if strategy is None or strategy==strategyId:
					nodes.append(node)
			self._filteredNodesCache[key] = nodes
			# self.logger.debug("getNodesForStrategy(%s) = %s", strategyId, nodes)
		return nodes

	def getHoursRanges(self):
		"""
		Return a concatenation of all offpeak ours off sources.
		"""
		offpeakhours = []
		nb = 0
		for elem in self.getAll("publicpowergrid"):
			offpeakhours = elem.getContract().getHoursRanges()
			nb += 1
		if nb==0:
			self.logger.warning("No PublicPowerGrid on the network.")
		return offpeakhours

	def getPrice(self, now=None, attime=None):
		"""
		Estimate what should be the electricity cost at a Time.
		If time is None, set to now
		return : float: cost
		 (should be allways the same so never mind for comparaison)
		"""
		cost = 0
		for elem in self.getAll("publicpowergrid"):
			cost = elem.getContract().getPrice(now, attime)
			return cost
		return cost

	def getSellPrice(self, now=None, attime=None):
		"""
		Estimate what should be the electricity sell cost at a Time.
		If time is None, set to now"
		"""
		cost = 0
		for elem in self.getAll("publicpowergrid"):
			cost = elem.getContract().getSellPrice(now, attime)
			return cost
		return cost

	def getTime(self):
		"""
		Get current time
		"""
		return self.server.getTime()
