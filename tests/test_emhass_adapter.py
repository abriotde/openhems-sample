#!/usr/bin/env python3
"""
Check common functionnality
 of openhems.modules.energy_strategy.offpeak_strategy.OffPeakStrategy
"""

import sys
from pathlib import Path
import unittest
import pandas
# pylint: disable=wrong-import-position
# pylint: disable=import-error
sys.path.append(str(Path(__file__).parents[1] / "src"))
from openhems.modules.energy_strategy.driver.emhass_adapter import (
	Deferrable,
	EmhassAdapter
)

class TestEmhassAdapter(unittest.TestCase):
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
		self.assertEqual(type(data) , pandas.core.frame.DataFrame)
		for timestamp, row in data.iterrows():
			print("timestamp:", type(timestamp)) # pandas._libs.tslibs.timestamps.Timestamp
			for index, _ in enumerate(deferables):
				val = row.get('P_deferrable'+str(index), None)
				print("> ",timestamp.to_pydatetime(), " [",index,"] => ", val)
				self.assertTrue(val is not None)

	def test_setDeferrables(self):
		"""
		Test if we can use EmhassAdapter and change on live deferables
		"""
		emhass = EmhassAdapter.createForOpenHEMS()
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

if __name__ == '__main__':
	unittest.main()
