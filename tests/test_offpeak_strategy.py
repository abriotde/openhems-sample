#!/usr/bin/env -S python3
"""
Test OffpeakStrategy class
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime
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
		# Force offpeak, near peak-timeslot
		now = datetime(2025, 4, 10, hour=5, minute=30, second=0)
		self.init(configFile, now=now)
		logger.info("Now: %s",now.strftime("%d/%m/%Y, %H:%M:%S"))
		# Appliances ordered by priority
		nodesIds = ["pump", "car", "machine"]
		self.setNodesValues(nodesIds,
			scheduledDurations=[3600, 3600, 3600],
			scheduledTimeout=[
				datetime(2025, 4, 10, 8, 0, 0),
				datetime(2025, 4, 10, 23, 0, 0),
				None
			]
		)
		self.loop()
		# Check switch on just pump : with the most priority
		self.checkValues(nodesIds, [280, 1800, 0], marginPower=2100)
		self.loop()
		# Check switch on just machine : with the most priority next
		self.checkValues(nodesIds, [280, 1800, 0], marginPower=20)
		# Check result with no switch on more due to reach maxPower-marginPower occured.
		# marginPower: 1000, maxPower: 3100
		self.loop()
		self.checkValues(nodesIds, [280, 1800, 0], marginPower=20)
		# Check result after force switch on car : reach maxPower-marginPower
		# Switch off machine
		self.setNodesValues(["machine"], switchOn=[True])
		self.loop()
		self.checkValues(nodesIds, [280, 1800, 0])
		# Set a scheduled node to a duration and check if it is switch on and duration decrease
		self.loop()
		self.checkValues(nodesIds, [280, 1800, 0], marginPower=20, scheduledDurations=[
			3570, # 30 = 16 + 8 + 4 + 2
			3570, # 30 = 16 + 8 + 4 + 2
			3600  # 0
		])
		# Check durations are correct. As each was a unique power of 2, we can identify errors
		now = now.replace(hour=5, minute=58, second=10)
		self.loop(now=now)
		now = now.replace(hour=6, minute=0, second=10)
		self.loop(now=now)
		now = now.replace(hour=6, minute=0, second=30)
		self.loop(now=now)
		self.checkValues(nodesIds, [280, 0, 0], marginPower=2100, scheduledDurations=[
			1791,
			1791,
			3600
		])
		now = now.replace(hour=6, minute=30, second=22)
		self.loop(now=now)
		self.checkValues(nodesIds, [0, 0, 0], marginPower=1820, scheduledDurations=[
			0,
			1791,
			3600
		])
		now = now.replace(hour=6, minute=30, second=10)
		self.loop(now=now)
		self.checkValues(nodesIds, [0, 0, 0], marginPower=2100, scheduledDurations=[
			0,
			1791,
			3600
		])
		now = now.replace(hour=22, minute=1, second=0)
		self.loop(now=now)
		now = now.replace(hour=22, minute=2, second=0)
		self.loop(now=now)
		self.checkValues(nodesIds, [0, 1800, 0], marginPower=-500, scheduledDurations=[
			0,
			1731,
			3600
		])
		now = now.replace(hour=22, minute=40, second=0)
		self.loop(now=now)
		self.checkValues(nodesIds, [0, 0, 0], marginPower=300, scheduledDurations=[
			0,
			0,
			3600
		])
		now = now.replace(hour=23, minute=0, second=0)
		self.loop(now=now)
		self.checkValues(nodesIds, [0, 0, 800], marginPower=2100, scheduledDurations=[
			0,
			0,
			3600
		])
		now = now.replace(hour=23, minute=59, second=59)
		self.loop(now=now)
		self.checkValues(nodesIds, [0, 0, 800], marginPower=1300, scheduledDurations=[
			0,
			0,
			1
		])


	def test_missingKeyParameters(self):
		"""
		Test behaviour when missing key parameters 
		"""
		# Test when missing currentPower of publicpowergrid
		# publicpowergrid should not be present,
		# but server must work with error message in GET /params
		configFile = utils.ROOT_PATH / "tests/data/openhems_fake4tests_missingKeyParams.yaml"
		self.assertIsNone(self.init(configFile))
		expectedWarnings = [
			"Impossible to load publicpowergrid",
			"OffPeak-strategy is useless without offpeak hours."
		]
		print("Warnings: ",self.app.warnings)
		for warning in expectedWarnings:
			self.assertTrue(
				any(warning in expectedWarning for expectedWarning in self.app.warnings),
				f"Warning not found: {warning}"
			)

	def test_fakeCallHomeAssistant(self):
		"""
		Test if server start well with HomeAssistant adapter with fake url
		"""
		configFile = utils.ROOT_PATH / "tests/data/openhems.yaml"
		self.init(configFile)
		expectedWarnings = ["Max retries exceeded with url: /api/states", " timed out"]
		for warning in expectedWarnings:
			self.assertTrue(
				any(warning in expectedWarning for expectedWarning in self.app.warnings),
				f"Warning not found: {warning}"
			)

if __name__ == '__main__':
	unittest.main()
