#!/usr/bin/env -S python3
"""
Test OffpeakStrategy class
"""

import sys
import unittest
from pathlib import Path
import datetime
import logging
# pylint: disable=wrong-import-position, import-error
sys.path.append(str(Path(__file__).parents[0]))
import utils

logger = logging.getLogger(__name__)

class TestOffpeakStrategy(utils.TestStrategy):
	"""
	Try test wall core server (OpenHEMS part, not web part)
	"""

	# pylint: disable=invalid-name
	def test_runServer(self):
		"""
		Test if server start well with FakeNetwork adapter
		"""
		configFile = utils.ROOT_PATH / "tests/data/openhems_fake4tests.yaml"
		# print("test_runServer()")
		self.init(configFile)
		now = datetime.datetime.now()
		now = now.replace(hour=23, minute=0, second=0) # Force offpeak
		logger.info("Now: %s",now.strftime("%d/%m/%Y, %H:%M:%S"))
		nodes = self.firstLoop(now)
		car = nodes["car"]
		pump = nodes["pump"]
		machine = nodes["machine"]
		self.assertEqual(pump.getCurrentPower(), 280)
		self.assertEqual(car.getCurrentPower(), 0)
		self.assertEqual(machine.getCurrentPower(), 0)
		self.assertEqual(self.getNetwork().getMarginPowerOn(), 2100)
		self.app.server.loop(1, now)
		self.assertEqual(car.getCurrentPower(), 0)
		self.assertEqual(machine.getCurrentPower(), 800)
		self.assertEqual(pump.getCurrentPower(), 280)
		self.assertEqual(self.getNetwork().getMarginPowerOn(), 1820)
		self.app.server.loop(1, now)
		self.assertEqual(car.getCurrentPower(), 0)
		self.assertEqual(machine.getCurrentPower(), 800)
		self.assertEqual(pump.getCurrentPower(), 280)
		self.assertEqual(self.getNetwork().getMarginPowerOn(), 1020)
		car.switchOn(True)
		self.app.server.loop(1, now)
		self.assertEqual(car.getCurrentPower(), 1800)
		self.assertEqual(machine.getCurrentPower(), 0)
		self.assertEqual(pump.getCurrentPower(), 280)
		self.assertEqual(self.getNetwork().getMarginPowerOn(), -780)

	# pylint: disable=invalid-name
	def test_xxx(self):
		"""
		Test 
		"""

if __name__ == '__main__':
	unittest.main()
