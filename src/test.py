#!/usr/bin/env python3
import unittest
from server import OffPeakStrategy

print("Tests:")

class TestOffPeakStrategy(unittest.TestCase):

    def test_checkRange(self):
        # Check range contains midnight
        t = OffPeakStrategy([["22:00:00","06:00:00"]])
        # Check for sensitive time for midnight
        t.checkRange(230000)
        self.assertTrue(t.inOffpeakRange)
        # Check for not o'clock time
        t.checkRange(63000)
        self.assertFalse(t.inOffpeakRange)
        self.assertEqual(t.rangeEnd, 220000)
        # Check for 2 ranges
        t = OffPeakStrategy([["10:00:00","11:30:00"],["14:00:00","16:00:00"]])
        t.checkRange(150000)
        self.assertTrue(t.inOffpeakRange)
        self.assertEqual(t.rangeEnd, 160000)
        t.checkRange(230000)
        self.assertFalse(t.inOffpeakRange)
        self.assertEqual(t.rangeEnd, 100000)
        # Check in middle of 2 range
        t.checkRange(123456)
        self.assertFalse(t.inOffpeakRange)
        self.assertEqual(t.rangeEnd, 140000)

# if __name__ == '__main__':
unittest.main()
