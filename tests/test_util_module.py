#!/usr/bin/env python3
"""
Check common functionnality
 of openhems.modules.energy_strategy.offpeak_strategy.OffPeakStrategy
"""

import sys
import unittest
from pathlib import Path
import logging
# pylint: disable=wrong-import-position
# pylint: disable=import-error
sys.path.append(str(Path(__file__).parents[1] / "src"))
from openhems.modules.util.configuration_manager import ConfigurationManager
from openhems.modules.util.cast_utility import CastUtililty, CastException
ROOT_PATH = Path(__file__).parents[1]

logger = logging.getLogger(__name__)

class TestConfigurationManager(unittest.TestCase):
	"""
	Check common functionnality of util module (openhems.modules.util)
	"""

	# pylint: disable=invalid-name
	def test_configurationsManager(self):
		"""
		Test default values/overridden/singleton/unknown key
		"""
		configurator = ConfigurationManager(logger)

		# Test default values
		value = configurator.get("api.url")
		self.assertEqual(value, 'http://192.168.1.202:8123/api')
		value = configurator.get("server.logfile")
		self.assertEqual(value, '/var/log/openhems.log')

		# Test overriden configurations values
		configurator.addYamlConfig(ROOT_PATH / 'config/openhems.yaml')
		value = configurator.get("server.logfile")
		self.assertEqual(value, 'openhems.log')

		# Test singleton
		configurator2 = ConfigurationManager(logger)
		value = configurator2.get("server.logfile")
		self.assertEqual(value, 'openhems.log')

		# Test Invalid key
		value = configurator2.get("toto")
		self.assertIsNone(value)

	def test_castUtility(self):
		"""
		Test Cast
		"""
		# Cast Str => Int
		value = CastUtililty.toType('int', '2')
		self.assertEqual(value, 2)
		with self.assertRaises(CastException) as _:
			value = CastUtililty.toType('int', 'unavailable')

		# Str => Bool
		value = CastUtililty.toType('bool', '1')
		self.assertEqual(value, True)
		value = CastUtililty.toType('bool', '0')
		self.assertEqual(value, False)
		# Int => Bool
		value = CastUtililty.toType('bool', 3)
		self.assertEqual(value, True)
		value = CastUtililty.toType('bool', 0)
		self.assertEqual(value, False)

if __name__ == '__main__':
	unittest.main()
