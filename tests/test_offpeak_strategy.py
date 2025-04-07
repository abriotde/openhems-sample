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
		nodes = self.firstLoop(now) # Init all schedules to 3600
		# Appliances ordered by priority
		pump = nodes["pump"]
		car = nodes["car"]
		machine = nodes["machine"]
		# Check switch on just pump : with the most priority
		self.assertEqual(pump.getCurrentPower(), 280)
		self.assertEqual(car.getCurrentPower(), 0)
		self.assertEqual(machine.getCurrentPower(), 0)
		self.assertEqual(self.getNetwork().getMarginPowerOn(), 2100)
		self.app.server.loop(1, now)
		# Check switch on just machine : with the most priority next
		self.assertEqual(pump.getCurrentPower(), 280)
		self.assertEqual(car.getCurrentPower(), 0)
		self.assertEqual(machine.getCurrentPower(), 800)
		self.assertEqual(self.getNetwork().getMarginPowerOn(), 1820)
		# Check result with no switch on more due to reach maxPower+marginPower occured.
		# marginPower: 1000, maxPower: 3100
		self.app.server.loop(2, now)
		self.assertEqual(pump.getCurrentPower(), 280)
		self.assertEqual(car.getCurrentPower(), 0)
		self.assertEqual(machine.getCurrentPower(), 800)
		self.assertEqual(self.getNetwork().getMarginPowerOn(), 1020)
		# Check result after force switch on car
		car.switchOn(True)
		self.app.server.loop(4, now)
		self.assertEqual(pump.getCurrentPower(), 280)
		self.assertEqual(car.getCurrentPower(), 1800)
		self.assertEqual(machine.getCurrentPower(), 0)
		# Set a scheduled node to a duration and check if it is switch on and duration decrease
		self.app.server.loop(8, now)
		self.assertEqual(self.getNetwork().getMarginPowerOn(), 20)
		self.assertEqual(pump.getCurrentPower(), 280)
		self.assertEqual(car.getCurrentPower(), 1800)
		self.assertEqual(machine.getCurrentPower(), 0)
		# Check durations are correct. As each was a unique power of 2, we can identify errors
		self.assertEqual(pump.getSchedule().duration, 3589) # 11 = 8 + 2 + 1
		self.assertEqual(car.getSchedule().duration, 3592) # 8
		self.assertEqual(machine.getSchedule().duration, 3598) # 2

	def missingKeyParameters(self):
		"""
		Test behaviour when missing key parameters 
		"""
		# Test when missing currentPower of publicpowergrid
		# publicpowergrid should not be present,
		# but server must work with error message in GET /params
		configFile = utils.ROOT_PATH / "tests/data/openhems_fake4tests_missingKeyParams.yaml"
		self.init(configFile)
		self.assertIsNone(self.app.server)
		expectedWarnings = [
			"Impossible to convert currentPower",
			"OffPeak-strategy is useless without offpeak hours."
		]
		for warning in self.app.warnings:
			self.assertTrue(
				any(expectedWarning in warning for expectedWarning in expectedWarnings),
				f"Warning not found: {warning}"
			)

	def fakeCallHomeAssistant(self):
		"""
		Test if server start well with HomeAssistant adapter with fake url
		"""
		configFile = utils.ROOT_PATH / "tests/data/openhems.yaml"
		self.init(configFile)
		expectedWarnings = ["Max retries exceeded with url: /api/states", " timed out"]
		for warning in self.app.warnings:
			self.assertTrue(
				any(expectedWarning in warning for expectedWarning in expectedWarnings),
				f"Warning not found: {warning}"
			)

if __name__ == '__main__':
	unittest.main()
