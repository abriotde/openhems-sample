#!/usr/bin/env python3
import unittest
from datetime import datetime
from energy_strategy import OffPeakStrategy


class TestOffPeakStrategy(unittest.TestCase):

	def test_checkRange(self):
		# print("test_checkRange")
		# Check range contains midnight
		t = OffPeakStrategy(None, [["22:00:00","06:00:00"]])
		# Check for sensitive time for midnight
		s = t.checkRange(datetime(2024, 7, 11, 23, 00, 00))
		self.assertTrue(t.inOffpeakRange)
		# Check for not o'clock time
		s = t.checkRange(datetime(2024, 7, 11, 6, 30, 00))
		self.assertFalse(t.inOffpeakRange)
		self.assertEqual(t.rangeEnd.strftime("%H%M%S"), "220000")
		# Check for 2 ranges
		t = OffPeakStrategy(None, [["10:00:00","11:30:00"],["14:00:00","16:00:00"]])
		s = t.checkRange(datetime(2024, 7, 11, 15, 00, 00))
		self.assertTrue(t.inOffpeakRange)
		self.assertEqual(t.rangeEnd.strftime("%H%M%S"), "160000")
		s = t.checkRange(datetime(2024, 7, 11, 23, 00, 00))
		self.assertFalse(t.inOffpeakRange)
		self.assertEqual(t.rangeEnd.strftime("%H%M%S"), "100000")
		# Check in middle of 2 range
		s = t.checkRange(datetime(2024, 7, 11, 12, 34, 56))
		self.assertFalse(t.inOffpeakRange)
		self.assertEqual(t.rangeEnd.strftime("%H%M%S"), "140000")

# if __name__ == '__main__':
unittest.main()

