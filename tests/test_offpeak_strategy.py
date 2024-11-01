#!/usr/bin/env python3
"""
Check common functionnality
 of openhems.modules.energy_strategy.offpeak_strategy.OffPeakStrategy
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path
# pylint: disable=wrong-import-position
sys.path.append(str(Path(__file__).parents[1] / "src"))
from openhems.modules.energy_strategy.offpeak_strategy import OffPeakStrategy

class TestOffPeakStrategy(unittest.TestCase):
	"""
	Check common functionnality
	 of openhems.modules.energy_strategy.offpeak_strategy.OffPeakStrategy
	"""

	# pylint: disable=invalid-name
	def test_checkRange(self):
		"""
		Test range system.
		Init from different kind off-peak range and test some off-peak hours.
		"""
		# print("test_checkRange")
		# Check range contains midnight
		t = OffPeakStrategy(None, [["22:00:00","06:00:00"]])
		# Check for sensitive time for midnight
		t.checkRange(datetime(2024, 7, 11, 23, 00, 00))
		self.assertTrue(t.inOffpeakRange)
		# Check for not o'clock time
		t.checkRange(datetime(2024, 7, 11, 6, 30, 00))
		self.assertFalse(t.inOffpeakRange)
		self.assertEqual(t.rangeEnd.strftime("%H%M%S"), "220000")
		# Check for 2 ranges
		t = OffPeakStrategy(None, [["10:00:00","11:30:00"],["14:00:00","16:00:00"]])
		t.checkRange(datetime(2024, 7, 11, 15, 00, 00))
		self.assertTrue(t.inOffpeakRange)
		self.assertEqual(t.rangeEnd.strftime("%H%M%S"), "160000")
		t.checkRange(datetime(2024, 7, 11, 23, 00, 00))
		self.assertFalse(t.inOffpeakRange)
		self.assertEqual(t.rangeEnd.strftime("%H%M%S"), "100000")
		# Check in middle of 2 range
		t.checkRange(datetime(2024, 7, 11, 12, 34, 56))
		self.assertFalse(t.inOffpeakRange)
		self.assertEqual(t.rangeEnd.strftime("%H%M%S"), "140000")

if __name__ == '__main__':
	unittest.main()
