"""
This is a fake network for tests.
  Values are set random
  or from specific data set.
"""

import re
import datetime
import time
from openhems.util import CastUtililty
from openhems.modules.network.network import HomeStateUpdater
from openhems.modules.network.feeder import (
	Feeder, RandomFeeder, ConstFeeder, RotationFeeder, FakeSwitchFeeder, StateFeeder
)
from openhems.modules.network.node import OutNode

regexpRandomFeeder = re.compile(r'^RANDOM\( *([0-9]+(.[0-9]+)?) *,'
	' *([0-9]+(.[0-9]+)?) *, *([0-9]+(.[0-9]+)?) *)$')
todays_Date = datetime.date.fromtimestamp(time.time())
date_in_ISOFormat = todays_Date.isoformat()

class FakeNetwork(HomeStateUpdater):
	"""
	This is a fake network for tests.
	"""

#	def __init__(self, conf) -> None:
#		super().__init__(conf)

	# pylint: disable=unused-argument
	def getFeeder(self, conf, key, expectedType=None, default_value=None) -> Feeder:
		"""
		Return a feeder considering
		 if the "key" can be a Home-Assistant element id.
		 Otherwise, it consider it as constant.
		"""
		feeder = None
		key = conf.get(key, None)
		if isinstance(key, str):
			key = key.strip().upper()
			if regexpRandomFeeder.match(key):
				vals = regexpRandomFeeder.match(key)
				self.logger.info("RandomFeeder(%s, %s, %s)", vals[1], vals[3], vals[5])
				feeder = RandomFeeder(self, float(vals[1]), float(vals[3]), float(vals[5]))
			else:
				self.logger.info("ConstFeeder(%s) - default str", key)
				feeder = ConstFeeder(float(key))
		elif isinstance(key, list):
			self.logger.info("RotationFeeder(%s)", key)
			feeder = RotationFeeder(self, key)
		elif default_value is not None:
			self.logger.info("ConstFeeder(%s) - default_value", default_value)
			feeder = ConstFeeder(default_value)
		else:
			self.logger.info("ConstFeeder(%s) - default", key)
			feeder = ConstFeeder(key)
		return feeder

	def getSwitch(self, nameid, nodeConf):
		currentPower = self.getFeeder(nodeConf, "currentPower")
		_isOn = CastUtililty.toTypeBool(nodeConf.get('isOn', True))
		self.logger.info("StateFeeder(%s)", str(_isOn))
		isOn = StateFeeder(_isOn)
		maxPower = self.getFeeder(nodeConf, "maxPower", 2000)
		currentPowerRealisttic = FakeSwitchFeeder(currentPower, isOn)
		node = OutNode(nameid, currentPowerRealisttic, maxPower, isOn)
		return node


	def switchOn(self, isOn:bool, node):
		"""
		return: True if the switch is on after, False else
		"""
		# pylint: disable=protected-access
		node._isOn.setValue(isOn) # (Should do in an other way?)
		return node.isOn()
