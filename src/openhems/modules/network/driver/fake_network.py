"""
This is a fake network for tests.
  Values are set random
  or from specific data set.
"""

import re
from openhems.modules.util.cast_utility import CastUtililty
from openhems.modules.network import (
	HomeStateUpdater,
	Feeder, RandomFeeder, ConstFeeder, RotationFeeder, StateFeeder, SumFeeder
)

RANDOM_FEEDER = r'^RANDOM\( *([0-9]+(.[0-9]+)?) *, *([0-9]+(.[0-9]+)?) *, *([0-9]+(.[0-9]+)?) *\)$'
REGEXP_RANDOM_FEEDER = re.compile(RANDOM_FEEDER)
REGEXP_SUM_FEEDER = re.compile(r'^SUM\( *([a-zA-Z]+) *\)$')

class FakeNetwork(HomeStateUpdater):
	"""
	This is a fake network for tests.
	"""

#	def __init__(self, conf) -> None:
#		super().__init__(conf)

	def getFeeder(self, value, expectedType=None, defaultValue=None, nameid="", node=None) -> Feeder:
		"""
		Return a feeder considering
		 if the "key" can be a Home-Assistant element id.
		 Otherwise, it consider it as constant.
		"""
		feeder = None
		if nameid=="switch.isOn":
			_isOn = CastUtililty.toTypeBool(value)
			feeder = StateFeeder(_isOn)
			node.setFakeSwitchFeeder(feeder)
			return feeder
		# print("getFeeder(",value, expectedType, defaultValue, ")")
		if isinstance(value, str):
			value = value.strip().upper()
			if REGEXP_RANDOM_FEEDER.match(value):
				vals = REGEXP_RANDOM_FEEDER.match(value)
				# self.logger.debug("RandomFeeder(%s, %s, %s)", vals[1], vals[3], vals[5])
				feeder = RandomFeeder(self, float(vals[1]), float(vals[3]), float(vals[5]))
			if REGEXP_SUM_FEEDER.match(value):
				vals = REGEXP_SUM_FEEDER.match(value)
				# self.logger.debug("SumFeeder(%s)", vals[1])
				feeder = SumFeeder(self.network, vals[1])
			else:
				self.logger.debug("ConstFeeder(%s) - default str", value)
				feeder = ConstFeeder(value, None, expectedType)
		elif isinstance(value, list):
			# self.logger.debug("RotationFeeder(%s)", value)
			feeder = RotationFeeder(self, value)
		elif defaultValue is not None:
			# self.logger.debug("ConstFeeder(%s) - defaultValue", defaultValue)
			feeder = ConstFeeder(defaultValue, None, expectedType)
		else:
			# self.logger.debug("ConstFeeder(%s) - default", value)
			feeder = ConstFeeder(value, None, expectedType)
		return feeder

	def switchOn(self, isOn:bool, node):
		"""
		return: True if the switch is on after, False else
		"""
		# pylint: disable=protected-access
		node._isOn.setValue(isOn) # (Should do in an other way?)
		return node.isOn()

	def notify(self, message, printer=None):
		"""
		Test notify function
		"""
		if printer is None:
			printer = print
		printer(f"FakeNetwork.notify({message})")
