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

	# pylint: disable=invalid-name
	def test_rteTempoColors(self):
		"""
		Test default values/overridden/singleton/unknown key
		"""
		# print("test_configurationsManager()")
		contract = RTETempoContract(color=None, colorNext=None,
	             offpeakprices=[0.1, 0.2, 0.3], peakprices = [0.4, 0.5, 0.6],
	             offpeakHoursRanges=["6h-22h"])
		self.assertEqual(contract.callApiRteTempo("2025-03-02"), "bleu")
		self.assertEqual(contract.callApiRteTempo("2025-03-03"), "blanc")
		self.assertEqual(contract.callApiRteTempo("2025-02-03"), "rouge")
		mydate = datetime.strptime("2025-02-03 05:59:54", "%Y-%m-%d %H:%M:%S")
		self.assertEqual(contract.getColorDate(mydate), "2025-02-02")
		c1 = contract.getNextColor()
		c2 = contract.getNextColor()
		self.assertEqual(c1, c2)
		c1 = contract.getCurColor()
		c2 = contract.getCurColor()
		self.assertEqual(c1, c2)

if __name__ == '__main__':
	unittest.main()
