"""
This module aim to abstract home network of connected devices.
It is used to know devices and to switch on/off them.
"""

from typing import Final
import copy
from openhems.modules.util.notification_manager import NotificationManager
from .node import (
	OpenHEMSNode, InOutNode, OutNode, PublicPowerGrid, SolarPanel, Battery
)
from .homestate_updater import HomeStateUpdater

POWER_MARGIN: Final[int] = 10 # Margin of power consumption for security

# pylint: disable=too-many-public-methods
class OpenHEMSNetwork:
	"""
	This class aim to abstract home network of connected devices.
	It is used to know devices and to switch on/off them.
	"""
	networkUpdater: HomeStateUpdater = None

	def print(self, printer=None):
		"""
		Print OpenHEMSNetwork as human readable string
		"""
		if printer is None:
			printer = print
		printer("OpenHEMSNetwork(")
		printer(" IN : ")
		for elem in self.getAll("inout"):
			printer("  - "+str(elem))
		printer(" OUT : ")
		for elem in self.getAll("out"):
			printer("  - "+str(elem))
		printer(")")

	def __init__(self, logger, networkUpdater, nodesConf):
		self.networkUpdater = None
		self.nodes = []
		self.notificationManager = None
		self._elemsCache = {}
		self.logger = logger
		self._loopNb = 0 # used for cache (if loopNb didn't move, get from cache)
		self._loopNbMarginPowerOn = -1
		self._marginPowerOn = -1
		self.addNetworkUpdater(networkUpdater, nodesConf)

	def addNetworkUpdater(self, networkUpdater: HomeStateUpdater, nodesConf):
		"""
		Add a networkUpdater (HomeStateUpdater) with is required.
		"""
		# print("addNetworkUpdater()")
		networkUpdater.initNetwork(self)
		networkUpdater.getNetwork(nodesConf)
		self.networkUpdater = networkUpdater
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

	def addNode(self, elem: OpenHEMSNode) -> OpenHEMSNode:
		"""
		Add a node.
		"""
		elem.network = self
		self.nodes.append(elem)
		self._elemsCache = {}
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
		out = self._elemsCache.get(filterId, None)
		if out is None:
			if elemFilter is None:
				filters = {
					"inout" : (lambda x: isinstance(x, InOutNode)),
					"out" : (lambda x: isinstance(x, OutNode)),
					"publicpowergrid" : (lambda x: isinstance(x, PublicPowerGrid)),
					"battery" : (lambda x: isinstance(x, Battery)),
					"solarpanel" : (lambda x: isinstance(x, SolarPanel)),
				}
				elemFilter = filters.get(filterId, None)
			if elemFilter is not None:
				out = list(filter(elemFilter, self.nodes))
				if filterId=="out":
					out.sort(
						reverse=True, key=lambda x:x.getPriority()
					)
			elif filterId=="":
				out = self.nodes
			else:
				self.logger.error("Network.getAll() : unknown filterId '%s'",
					 filterId)
				out = None
			self._elemsCache[filterId] = out
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
		"""
		return self._sumNodesValues("out", "out", (lambda x: x.isOn() and x.getMaxPower()))

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
		return self._sumNodesValues(filterId, "inout", (lambda x: x.getMarginPower()))

	def getMarginPowerOn(self):
		"""
		Get how many power we can add safely
		"""
		if self._loopNbMarginPowerOn != self._loopNb:
			# The maximum production before black-out
			maxPowerP = self.getMaxPowerProduction()
			# The consumption if every switched on devices consume at max capability
			maxPowerC = self.getMaxPowerConsumption()
			currentPower = self.getCurrentPower()
			marginPower = self.getMarginPower()
			# self.logger.debug(
			#	"MaxPowerProduction:%s; MaxPowerConsumption:%s; CurrentPower:%s; MarginPower:%s;",
			#	maxPowerP, maxPowerC, currentPower, marginPower)
			self._marginPowerOn = min(
				maxPowerP-(currentPower+marginPower),
				maxPowerP-maxPowerC # Maybe is it too safe?
			)
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
			if elem.isSwitchable and elem.switchOn(False):
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
		nodes = self._elemsCache.get(key, None)
		if nodes is None:
			# self.logger.debug("getNodesForStrategy() : generate cache")
			nodes = []
			for node in self.getAll("out"):
				strategy = node.getStrategyId()
				if strategy is None or strategy==strategyId:
					nodes.append(node)
			self._elemsCache[key] = nodes
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
		for elem in self.getAll("publicpowergrid"):
			cost = elem.getContract().getPrice(now, attime)
			return cost

	def getSellPrice(self, now=None, attime=None):
		"""
		Estimate what should be the electricity sell cost at a Time.
		If time is None, set to now"
		"""
		for elem in self.getAll("publicpowergrid"):
			cost = elem.getContract().getSellPrice(now, attime)
			return cost
