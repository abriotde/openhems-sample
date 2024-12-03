#!/usr/bin/env python3
"""
Check common functionnality
 of openhems.modules.energy_strategy.offpeak_strategy.OffPeakStrategy
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path
import logging
import io
import contextlib
import hashlib
# pylint: disable=wrong-import-position
# pylint: disable=import-error
ROOT_PATH = Path(__file__).parents[1]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.modules.network.driver.fake_network import FakeNetwork
from openhems.modules.util import (
	NotificationManager, MessageHistory,
	Time, HoursRanges,
	CastUtililty,
	CastException, ConfigurationManager
)

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

		curFolder = Path(__file__).parents[0]
		savedFile = curFolder / 'data/openhems_test_save.test.yaml'
		if savedFile.exists():
			savedFile.unlink()
		configurator.save(savedFile)
		referenceFile = curFolder / 'data/openhems_test_save.yaml'
		f1 = open(referenceFile)
		f2 = open(savedFile)
		self.assertListEqual( list(f1), list(f2) )
		f1.close()
		f2.close()

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

	# pylint: disable=invalid-name
	def test_checkRange(self):
		"""
		Test range system.
		Init from different kind off-peak range and test some off-peak hours.
		"""
		# print("test_checkRange")
		# Check range contains midnight
		offpeakRange = HoursRanges([["22:00:00","06:00:00"]])
		# Check for sensitive time for midnight
		inOffpeakRange, _ = offpeakRange.checkRange(
			datetime(2024, 7, 11, 23, 00, 00)
		)
		self.assertTrue(inOffpeakRange)
		# Check for not o'clock time
		inOffpeakRange, rangeEnd = offpeakRange.checkRange(
			datetime(2024, 7, 11, 6, 30, 00)
		)
		self.assertFalse(inOffpeakRange)
		self.assertEqual(rangeEnd.strftime("%H%M%S"), "220000")

		# Check for 2 ranges
		offpeakRange = HoursRanges(
			[["10:00:00","11:30:00"],["14:00:00","16:00:00"]]
		)
		inOffpeakRange, rangeEnd = offpeakRange.checkRange(
			datetime(2024, 7, 11, 15, 00, 00)
		)
		self.assertTrue(inOffpeakRange)
		self.assertEqual(rangeEnd.strftime("%H%M%S"), "160000")
		inOffpeakRange, rangeEnd = offpeakRange.checkRange(
			datetime(2024, 7, 11, 23, 00, 00)
		)
		self.assertFalse(inOffpeakRange)
		self.assertEqual(rangeEnd.strftime("%H%M%S"), "100000")
		# Check in middle of 2 range
		inOffpeakRange, rangeEnd = offpeakRange.checkRange(
			datetime(2024, 7, 11, 12, 34, 56)
		)
		self.assertFalse(inOffpeakRange)
		self.assertEqual(rangeEnd.strftime("%H%M%S"), "140000")


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
