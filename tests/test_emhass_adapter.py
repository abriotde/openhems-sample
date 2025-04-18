#!/usr/bin/env python3
"""
Check common functionnality
 of openhems.modules.energy_strategy.offpeak_strategy.OffPeakStrategy
"""

import sys
from pathlib import Path
import unittest
import logging
import pandas
# pylint: disable=import-error
import utils
# pylint: disable=wrong-import-position
ROOT_PATH = Path(__file__).parents[1]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.modules.energy_strategy.driver.emhass_adapter import (
	Deferrable,
	EmhassAdapter
)
# pylint: disable=wrong-import-position, import-error
sys.path.append(str(Path(__file__).parents[0]))

EMHASS_CONFIG_FILE = ROOT_PATH / "tests/data/openhems_test_emhass.yaml"
logger = logging.getLogger(__name__)

class TestEmhassAdapter(utils.TestStrategy):
	"""
	Check common functionnality
	 of openhems.modules.energy_strategy.offpeak_strategy.OffPeakStrategy
	"""

	# pylint: disable=invalid-name
	def evalDeferrables(self, emhass, deferables):
		"""
		Eval if data from emhass.performOptim() are correct according to deferables
		"""
		emhass.deferables = deferables
		data = emhass.performOptim()
		self.assertIsInstance(data, pandas.core.frame.DataFrame)
		self.assertEqual(type(data) , pandas.core.frame.DataFrame)
		for _, row in data.iterrows():
			# print("timestamp:", type(timestamp)) # pandas._libs.tslibs.timestamps.Timestamp
			for index, _ in enumerate(deferables):
				val = row.get('P_deferrable'+str(index), None)
				# print("> ",timestamp.to_pydatetime(), " [",index,"] => ", val)
				self.assertTrue(val is not None)

	def xtest_setDeferrables(self):
		"""
		Test if we can use EmhassAdapter and change on live deferables
		"""
		# TODO : give parameters to EmhassAdapter.createFromOpenHEMS()
		emhass = EmhassAdapter.createFromOpenHEMS()
		deferables = [
			Deferrable(1000, 3),
			Deferrable(300, 2),
			Deferrable(1500, 5)
		]
		self.evalDeferrables(emhass, deferables)
		deferables = [
			Deferrable(1000, 3)
		]
		self.evalDeferrables(emhass, deferables)
		deferables = [
			Deferrable(1000, 3)
		]
		self.evalDeferrables(emhass, deferables)

	def test_applyEmhassStrategy(self):
		"""
		Test range system.
		Init from different kind off-peak range and test some off-peak hours.
		"""
		# print("test_applyEmhassStrategy")
		self.init(EMHASS_CONFIG_FILE)
		self.loop()
		self.checkValues(["voiture"], [0])
		self.setNodesValues(["voiture"], scheduledDurations=[3600])
		self.loop()

if __name__ == '__main__':
	unittest.main()
