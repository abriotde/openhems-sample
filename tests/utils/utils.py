"""
Utils classes for tests
"""
import sys
import unittest
from pathlib import Path
# pylint: disable=wrong-import-position, import-error
ROOT_PATH = Path(__file__).parents[2]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.main import OpenHEMSApplication
from openhems.modules.energy_strategy.energy_strategy import LOOP_DELAY_VIRTUAL

class TestStrategy(unittest.TestCase):
	"""
	Class to factorize code for test strategies
	"""
	def init(self, configFile):
		"""
		Init the application
		"""
		# pylint: disable=attribute-defined-outside-init
		self.app = OpenHEMSApplication(configFile)
		self.nodes = {}

	def firstLoop(self, now=None):
		"""
		Used for first lopp and it's check
		"""
		self.app.server.loop(LOOP_DELAY_VIRTUAL, now)
		for node in self.getNetwork().getAll("out"):
			# logger.info("Node: %s is on:%s", node.id, node.isOn())
			node.getSchedule().setSchedule(3600)
			self.assertFalse(node.isOn())
			self.nodes[node.id] = node
		self.app.server.loop(1, now)
		return self.nodes

	def checkValues(self, nodesIds, values, marginPower=None):
		"""
		Check values of nodes
		"""
		for i, nodeId in enumerate(nodesIds):
			node = self.nodes.get(nodeId)
			self.assertEqual(node.getCurrentPower(), values[i])
		if marginPower is not None:
			self.assertEqual(self.getNetwork().getMarginPowerOn(), marginPower)

	def getNetwork(self):
		"""
		Return network
		"""
		return self.app.server.network
