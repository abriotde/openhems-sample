#!/usr/bin/env python3
"""
Test AnnealingStrategy class, 
"""

import unittest
import logging
# pylint: disable=wrong-import-position, import-error
from utils import TestStrategy, ROOT_PATH

logger = logging.getLogger(__name__)

class TestAnnealingStrategy(TestStrategy):
	"""
	Try test wall core server (OpenHEMS part, not web part)
	"""

	# pylint: disable=invalid-name
	def test_runServer(self):
		"""
		Test if server start well with FakeNetwork adapter
		"""
		configFile = ROOT_PATH / "tests/data/openhems_fake4tests_annealing.yaml"
		self.init(configFile)
		nodes = self.firstLoop()
		car = nodes["car"]
		machine = nodes["machine"]
		pump = nodes["pump"]
		self.assertEqual(car.getCurrentPower(), 0)
		self.assertEqual(machine.getCurrentPower(), 0)
		self.assertEqual(pump.getCurrentPower(), 0)
		self.assertEqual(self.getNetwork().getMarginPowerOn(), 2100)
		self.app.server.loop(1)
		self.assertEqual(car.getCurrentPower(), 0)
		self.assertEqual(machine.getCurrentPower(), 0)
		self.assertEqual(pump.getCurrentPower(), 0)


	# pylint: disable=invalid-name
	def test_xxx(self):
		"""
		TODO: more tests
		"""

if __name__ == '__main__':
	unittest.main()
