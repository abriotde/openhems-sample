#!/usr/bin/env python3
"""
Test server, 
TODO : Fake network
"""


import sys
import unittest
import logging
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
		app.server.loop(LOOP_DELAY_VIRTUAL)
		# pylint: disable=redundant-unittest-assert
		self.assertTrue(True)

if __name__ == '__main__':
	unittest.main()
