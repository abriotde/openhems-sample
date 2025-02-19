#!/usr/bin/env python3
"""
Test openhems as Pip package.
"""


import openhems
from openhems.modules.energy_strategy import LOOP_DELAY_VIRTUAL
import unittest
from pathlib import Path
# pylint: disable=wrong-import-position
# pylint: disable=import-error
ROOT_PATH = Path(__file__).parents[1]

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
		app = openhems.OpenHEMSApplication(configFile)
		app.server.loop(LOOP_DELAY_VIRTUAL)
		# pylint: disable=redundant-unittest-assert
		self.assertTrue(True)

if __name__ == '__main__':
	unittest.main()
