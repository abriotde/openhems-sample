#!/usr/bin/env python3
"""
Test AnnealingStrategy class, 
"""
import sys
import unittest
from pathlib import Path
import logging
# pylint: disable=wrong-import-position, import-error
sys.path.append(str(Path(__file__).parents[0]))
import utils

logger = logging.getLogger(__name__)

class TestAnnealingStrategy(utils.TestStrategy):
	"""
	Try test wall core server (OpenHEMS part, not web part)
	"""

	# pylint: disable=invalid-name
	def test_runServer(self):
		"""
		Test if server start well with FakeNetwork adapter
		"""
		configFile = utils.ROOT_PATH / "tests/data/openhems_fake4tests_solarnosell.yaml"
		self.init(configFile)
		nodesIds = ["pump", "car", "machine"]
		self.checkValues(nodesIds, [0, 0, 0], marginPower=2100)
		self.loop()
		self.checkValues(nodesIds, [0, 0, 0])


	# pylint: disable=invalid-name
	def test_withoutPublicPowerGrid(self):
		"""
		Test without public power grid.
		"""
		configFile = (utils.ROOT_PATH /
			"tests/data/openhems_fake4tests_solarnosell_withoutpublicpowergrid.yaml")
		self.init(configFile)
		nodesIds = ["pump", "car", "machine"]
		self.checkValues(nodesIds, [0, 0, 0], marginPower=-300)
		self.loop()
		self.checkValues(nodesIds, [0, 0, 0])

if __name__ == '__main__':
	unittest.main()
