#!/usr/bin/env python3
"""
Check common functionnality
 of openhems.modules.energy_strategy.offpeak_strategy.OffPeakStrategy
"""

import sys
import unittest
import logging
from pathlib import Path
# pylint: disable=wrong-import-position
# pylint: disable=import-error
sys.path.append(str(Path(__file__).parents[1] / "src"))
# from openhems.modules.energy_strategy.offpeak_strategy import OffPeakStrategy
logger = logging.getLogger(__name__)

class TestOffPeakStrategy(unittest.TestCase):
	"""
	Check common functionnality
	 of openhems.modules.energy_strategy.offpeak_strategy.OffPeakStrategy
	"""

if __name__ == '__main__':
	unittest.main()
