#!/usr/bin/env python3
"""
Test server, 
"""


import sys
import unittest
import logging
import datetime
from pathlib import Path
# pylint: disable=wrong-import-position
# pylint: disable=import-error
ROOT_PATH = Path(__file__).parents[1]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.main import OpenHEMSApplication
from openhems.modules.energy_strategy.energy_strategy import LOOP_DELAY_VIRTUAL
logger = logging.getLogger(__name__)

class TestOpenHEMSServer(unittest.TestCase):
	"""
	Try test wall core server (OpenHEMS part, not web part)
	"""

	# pylint: disable=invalid-name
	def test_runServer(self):
		"""
		Test if server start well with FakeNetwork adapter
		"""
		configFile = ROOT_PATH / "tests/data/openhems_fake4tests_annealing.yaml"
		# print("test_runServer()")
		app = OpenHEMSApplication(configFile)
		now = datetime.datetime.now()
		now = now.replace(hour=23, minute=0, second=0) # Force offpeak
		logger.info("Now: %s",now.strftime("%d/%m/%Y, %H:%M:%S"))
		app.server.loop(LOOP_DELAY_VIRTUAL, now)
		nodes = {}
		for node in app.server.network.getAll("out"):
			# logger.info("Node: %s is on:%s", node.id, node.isOn())
			node.getSchedule().duration = 3600
			self.assertFalse(node.isOn())
			nodes[node.id] = node
		app.server.loop(1, now)
		car = nodes["car"]
		machine = nodes["machine"]
		pump = nodes["pump"]
		self.assertEqual(car.getCurrentPower(), 0)
		self.assertEqual(machine.getCurrentPower(), 0)
		self.assertEqual(pump.getCurrentPower(), 0)
		self.assertEqual(app.server.network.getMarginPowerOn(), 2100)
		app.server.loop(1, now)
		self.assertEqual(car.getCurrentPower(), 0)
		self.assertEqual(machine.getCurrentPower(), 0)
		self.assertEqual(pump.getCurrentPower(), 0)

if __name__ == '__main__':
	unittest.main()
