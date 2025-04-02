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
# pylint: disable=wrong-import-position
# pylint: disable=import-error
ROOT_PATH = Path(__file__).parents[1]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.modules.contract import (
	RTETempoContract
)

logger = logging.getLogger(__name__)


class TestContractModule(unittest.TestCase):
	"""
	Check common functionnality of contract module (openhems.modules.util)
	"""
	DATETIME_STR_FORMAT = "%Y-%m-%d %H:%M:%S"
	def getContractRteTempo(self):
		"""
		Return a standard RteTempoContract
		"""
		contract = RTETempoContract(color=None, colorNext=None,
				offpeakprices={"bleu":0.1, "blanc":0.2, "rouge":0.3},
				peakprices = {"bleu":0.4, "blanc":0.5, "rouge":0.6})
		return contract

	# pylint: disable=invalid-name
	def test_rteTempoColors(self):
		"""
		Test default values/overridden/singleton/unknown key
		"""
		contract = self.getContractRteTempo()
		# print("test_configurationsManager()")
		self.assertEqual(contract.callApiRteTempo("2025-03-02"), "bleu")
		self.assertEqual(contract.callApiRteTempo("2025-03-03"), "blanc")
		self.assertEqual(contract.callApiRteTempo("2025-02-03"), "rouge")
		mydate = datetime.strptime("2025-02-03 05:59:54", self.DATETIME_STR_FORMAT)
		self.assertEqual(contract.getColorDate(mydate), "2025-02-02")
		# test caches
		c1 = contract.getNextColor()
		c2 = contract.getNextColor()
		self.assertEqual(c1, c2)
		c1 = contract.getCurColor()
		c2 = contract.getCurColor()
		self.assertEqual(c1, c2)

	def test_rteTempoHoursRanges(self):
		"""
		Test RteContract.getHoursRanges() change .
		Test HoursRanges change when occure timeout/timeStart.
		"""
		contract = self.getContractRteTempo()
		datetimes = [
			"2025-02-02 06:00:00",
			"2025-02-02 06:00:01",
			"2025-02-02 23:59:59",
			"2025-02-03 00:00:00",
			"2025-02-03 00:00:01",
			"2025-02-03 05:59:59", 
		]
		ok = False
		for dt in datetimes:
			mydate = datetime.strptime(dt, self.DATETIME_STR_FORMAT)
			hoursRange = contract.getHoursRanges(mydate)
			start = hoursRange.timeStart.strftime(self.DATETIME_STR_FORMAT)
			self.assertEqual(start, "2025-02-02 06:00:00", "Wrong timeStart")
			end = hoursRange.timeout.strftime(self.DATETIME_STR_FORMAT)
			self.assertEqual(end, "2025-02-03 06:00:00", "Wrong timeout")
			if not ok: # Test only once
				ok = True
				# test checkRange() when occure timeout
				mydate2 = datetime.strptime("2025-02-04 07:00:00", self.DATETIME_STR_FORMAT)
				inoffpeak, rangeEnd, cost = hoursRange.checkRange(mydate2)
				rangeEnd = rangeEnd.strftime(self.DATETIME_STR_FORMAT)
				self.assertFalse(inoffpeak)
				self.assertEqual(rangeEnd, "2025-02-04 22:00:00")
				self.assertEqual(cost, 0.4)
				# test checkRange() when occure timeStart
				mydate2 = datetime.strptime("2025-02-04 23:00:00", self.DATETIME_STR_FORMAT)
				inoffpeak, rangeEnd, cost = hoursRange.checkRange(mydate2)
				rangeEnd = rangeEnd.strftime(self.DATETIME_STR_FORMAT)
				self.assertTrue(inoffpeak, "In off-peak of 23:00:00")
				self.assertEqual(rangeEnd, "2025-02-05 06:00:00", "off-peak range end")
				self.assertEqual(cost, 0.1, "off-peak price red")

if __name__ == '__main__':
	unittest.main()
