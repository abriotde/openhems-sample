"""
Utils classes for tests
"""
import sys
import unittest
import datetime
import logging
from pathlib import Path
# pylint: disable=wrong-import-position, import-error
ROOT_PATH = Path(__file__).parents[2]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.main import OpenHEMSApplication
from openhems.modules.util import DATETIME_PRINT_FORMAT

logger = logging.getLogger(__name__)

class TestStrategy(unittest.TestCase):
	"""
	Class to factorize code for test strategies
	"""
	# pylint: disable=attribute-defined-outside-init
	def init(self, configFile, now=None):
		"""
		Init the application
		"""
		# pylint: disable=attribute-defined-outside-init
		self.app = OpenHEMSApplication(configFile)
		self.nodes = {}
		self._loopDelay = 1
		if now is None:
			now = datetime.datetime.now()
		self._now = now
		if self.app is None or self.app.server is None:
			return None
		self.app.server.allowSleep = False
		self.app.server.loop(now)
		for node in self.getNetwork().getAll("out"):
			# logger.info("Node: %s is on:%s", node.id, node.isOn())
			self.assertFalse(node.isOn())
			self.nodes[node.id] = node
		return self.nodes

	def loop(self, loopDelay=None, now=None):
		"""
		If set now, we jump to now
		Else by default loopDelay is double at each loop
		 it give unique loop
		"""
		if now is None:
			if loopDelay is None:
				loopDelay = self._loopDelay
			# print("loopDelay:",loopDelay)
			self._now += datetime.timedelta(seconds=loopDelay)
		else:
			if loopDelay is not None:
				self._loopDelay = loopDelay
			else:
				self._loopDelay = (now - self._now).total_seconds()
			self._now = now
		logger.debug("Time: %s, lastloop: %s s",
			self._now.strftime(DATETIME_PRINT_FORMAT), self._loopDelay)
		self.app.server.loop(self._now)
		self._loopDelay *= 2
		return self.nodes


	def setNodesValues(self, nodesIds,
			scheduledDurations=None,
			scheduledTimeout=None,
			switchOn=None):
		"""
		Set values of nodes
		"""
		for i, nodeId in enumerate(nodesIds):
			node = self.nodes.get(nodeId)
			if node is not None:
				if switchOn is not None:
					node.switchOn(switchOn[i])
				if scheduledDurations is not None:
					node.getSchedule().duration = scheduledDurations[i]
				if scheduledTimeout is not None:
					node.getSchedule().timeout = scheduledTimeout[i]
			else:
				print(f"Node {nodeId} not found in nodes")

	def checkValues(self, nodesIds, values,
			marginPower=None,
			scheduledDurations=None):
		"""
		Check values of nodes
		"""
		for i, nodeId in enumerate(nodesIds):
			node = self.nodes.get(nodeId)
			self.assertEqual(node.getCurrentPower(), values[i])
			if scheduledDurations is not None:
				schedule = node.getSchedule()
				self.assertEqual(schedule.duration, scheduledDurations[i])
		if marginPower is not None:
			self.assertEqual(self.getNetwork().getMarginPowerOn(), marginPower)

	def getNetwork(self):
		"""
		Return network
		"""
		return self.app.server.network
