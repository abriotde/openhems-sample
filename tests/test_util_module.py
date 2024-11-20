#!/usr/bin/env python3
"""
Check common functionnality
 of openhems.modules.energy_strategy.offpeak_strategy.OffPeakStrategy
"""

import sys
import unittest
from pathlib import Path
import logging
import io
import contextlib
# pylint: disable=wrong-import-position
# pylint: disable=import-error
ROOT_PATH = Path(__file__).parents[1]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.modules.util.configuration_manager import ConfigurationManager
from openhems.modules.util.cast_utility import CastUtililty, CastException
from openhems.modules.network.driver.fake_network import FakeNetwork
from openhems.modules.util.notification_manager import NotificationManager, MessageHistory

stdout_handler = logging.StreamHandler(stream=sys.stdout)
logging.basicConfig(
    level=logging.ERROR,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=[stdout_handler]
)
logger = logging.getLogger(__name__)


class TestUtilModule(unittest.TestCase):
	"""
	Check common functionnality of util module (openhems.modules.util)
	"""

	# pylint: disable=invalid-name
	def test_configurationsManager(self):
		"""
		Test default values/overridden/singleton/unknown key
		"""
		# print("test_configurationsManager()")
		defaultPath = ROOT_PATH / "data/openhems_default.yaml"
		configurator = ConfigurationManager(logger, defaultPath=defaultPath)

		# Test default values
		value = configurator.get("api.url")
		self.assertEqual(value, 'http://192.168.1.202:8123/api')
		value = configurator.get("server.logfile")
		self.assertEqual(value, 'openhems.log')

		# Test overriden configurations values
		configurator.addYamlConfig(ROOT_PATH / 'config/openhems.yaml')
		value = configurator.get("server.logfile")
		self.assertEqual(value, 'openhems.log')

		# Test Invalid key
		value = configurator.get("toto")
		self.assertIsNone(value)

	def test_castUtility(self):
		"""
		Test Cast
		"""
		# print("test_castUtility()")
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

	def test_notifyManager(self):
		"""
		Test NotificationManager class.
		"""
		# For 64 notifications, should output 3 lines:
		#   FakeNetwork.notify(A test message.)
		#   FakeNetwork.notify("A test message." occured 7 more times)
		#   FakeNetwork.notify("A test message." occured 56 more times)
		f = io.StringIO()
		with contextlib.redirect_stdout(f):
			networkUpdater = FakeNetwork(None)
			notificator = NotificationManager(networkUpdater, logger)
			fakeMessage = "A test message."
			# notificator.notify(fakeMessage)
			for _ in range(MessageHistory.COMPACT_SIZE*MessageHistory.COMPACT_SIZE):
				notificator.notify(fakeMessage)
			notificator.notify(fakeMessage)
			notificator.loop()
		output = f.getvalue().strip()
		length = len(output.split('\n'))
		self.assertTrue(length==3)

if __name__ == '__main__':
	unittest.main()
