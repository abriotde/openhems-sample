#!/usr/bin/env -S python3
"""
Test OffpeakStrategy class
"""

import sys
import random
import unittest
from pathlib import Path
from datetime import datetime
import logging
# pylint: disable=wrong-import-position, import-error
sys.path.append(str(Path(__file__).parents[0]))
import utils

logger = logging.getLogger(__name__)

class TestFeedbackSwitch(utils.TestStrategy):
	"""
	Try FeedbackSwitch
	"""
	def randomDT(self):
		"""
		:return: random number close to 1 seconds to get more realistics datas
		(and random for a usefull modelization).
		"""
		rand = random.uniform(0.8 , 1.2)
		return rand

	# pylint: disable=invalid-name
	def test_feedbackswitchCycle(self):
		"""
		Test feedbackSwitch work well during EVAL mode and RUN one.
		"""
		configFile = utils.ROOT_PATH / "tests/data/openhems_fake4tests_feedbackswitch.yaml"
		# print("test_runServer()")
		# Force offpeak, near peak-timeslot
		now = datetime(2025, 4, 10, hour=5, minute=30, second=0)
		self.init(configFile, now=now)
		logger.info("Now: %s",now.strftime("%d/%m/%Y, %H:%M:%S"))
		# Appliances ordered by priority
		nodes = self.loop(self.randomDT())
		nodesIds = ['pump']
		pump = nodes['pump']
		# Check pump stay up until it max value (from 12 to 23)
		# pylint: disable=protected-access
		for i in range(13):
			print(i," : ",pump)
			self.checkValues(nodesIds, [280], isOn=[True])
			self.loop(self.randomDT())
			pump._sensor.value += 1
		print("Reach max : ", pump._sensor.value)
		for i in range(11):
			print(i," : ",pump)
			self.checkValues(nodesIds, [0], isOn=[False])
			self.loop(self.randomDT())
			pump._sensor.value -= 1
		print("Reach min : ", pump._sensor.value)
		for i in range(11):
			print(i," : ",pump)
			self.checkValues(nodesIds, [280], isOn=[True])
			self.loop(self.randomDT())
			pump._sensor.value += 1
		print("Reach max : ", pump._sensor.value)
		for i in range(11):
			print(i," : ",pump)
			self.checkValues(nodesIds, [0], isOn=[False])
			self.loop(self.randomDT())
			pump._sensor.value -= 1
		print("Reach min : ", pump._sensor.value)
		self.loop(self.randomDT())
		self.checkValues(nodesIds, [280], isOn=[True])

if __name__ == '__main__':
	unittest.main()
