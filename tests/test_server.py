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
		configFile = ROOT_PATH / "tests/data/openhems_fake4tests.yaml"
		# print("test_runServer()")
		app = OpenHEMSApplication(configFile)
		now = datetime.datetime.now()
		now = now.replace(hour=23, minute=0, second=0) # Force offpeak
		logger.info("Now: %s",now.strftime("%d/%m/%Y, %H:%M:%S"))
		app.server.loop(LOOP_DELAY_VIRTUAL, now)
		nodes = app.server.network.getAll("out")
		for node in nodes:
			# logger.info("Node: %s is on:%s", node.id, node.isOn())
			node.getSchedule().duration = 3600
			self.assertFalse(node.isOn())
		app.server.loop(1, now)
		for node in nodes:
			logger.info("Node: %s is on:%s", node.id, node.isOn())
		app.server.loop(1, now)
		for node in nodes:
			logger.info("Node: %s is on:%s", node.id, node.isOn())
		app.server.loop(1, now)
		app.server.loop(1, now)
		self.assertTrue(True)

if __name__ == '__main__':
	unittest.main()
