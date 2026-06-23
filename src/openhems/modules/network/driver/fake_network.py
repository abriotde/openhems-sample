"""
This is a fake network for tests.
  Values are set random
  or from specific data set.
"""

import re
from datetime import datetime
from openhems.modules.util import DangerousStateException, CastUtililty
from openhems.modules.network import (
	HomeStateUpdater,
	Feeder, RandomFeeder, ConstFeeder, RotationFeeder, StateFeeder, SumFeeder, SolarFeeder
)
from openhems.modules.util.configuration_manager import ConfigurationManager

RANDOM_FEEDER = r'^RANDOM\( *([0-9]+(.[0-9]+)?) *, *([0-9]+(.[0-9]+)?) *, *([0-9]+(.[0-9]+)?) *\)$'
REGEXP_RANDOM_FEEDER = re.compile(RANDOM_FEEDER)
REGEXP_SUM_FEEDER = re.compile(r'^SUM\( *([a-zA-Z]+) *\)$')
REGEXP_SOLAR_FEEDER = re.compile(r'^SOLAR\( *([a-zA-Z]+) *\)$')

class FakeNetwork(HomeStateUpdater):
	"""
	This is a fake network for tests.
	"""

	def __init__(self, conf:ConfigurationManager=None) -> None:
		if conf is None:
			conf = ConfigurationManager()
		super().__init__(conf)
		starttime = conf.get("server.start_time", defaultValue="2024-01-01 00:00:00")
		self._time = datetime.strptime(starttime, "%Y-%m-%d %H:%M:%S").timestamp()

	def getFeeder(self, value,
			   *, expectedType=None, defaultValue=None, nameid="", node=None
			) -> Feeder:
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
			elif REGEXP_SUM_FEEDER.match(value):
				vals = REGEXP_SUM_FEEDER.match(value)
				# self.logger.debug("SumFeeder(%s)", vals[1])
				feeder = SumFeeder(self.network, vals[1])
			elif REGEXP_SOLAR_FEEDER.match(value):
				vals = REGEXP_SOLAR_FEEDER.match(value)
				# self.logger.debug("SolarFeeder(%s)", vals[1])
				feeder = SolarFeeder(self.network, vals[1])
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

	def getTime(self) -> datetime:
		"""
		Get current time
		"""
		return datetime.fromtimestamp(self._time)



	def listComponents(self):
		return [
			"currentcost.sensor",
			"tapo.switch",
			"tuya_ble.sensor",
			"backup",
			"ble_monitor.binary_sensor",
			"localtuya.remote",
			"logger",
			"http",
			"hacs",
			"cast",
			"device_tracker",
			"upnp.binary_sensor",
			"notify",
			"person",
			"sensor.rte_tempo_prochaine_couleur",
			"sensor.lixee_zlinky_tic_puissance_apparente",
			"switch.tz3000_2putqrmw_ts011f_commutateur",
			"sensor.tz3000_2putqrmw_ts011f_puissance",
			"switch.tz3000_2putqrmw_ts011f_commutateur_2",
			"sensor.tz3000_2putqrmw_ts011f_puissance_2",
		]

	def updateNetwork(self, cycleDuration:int=30, now=None):
		"""
		Update network, but as we ever know it's architecture,
		 we just have to update few values.
		"""
		self._time += cycleDuration
		super().updateNetwork(cycleDuration, now)
		energy = 0
		for node in self.network.getAll("out"):
			if node.isOn():
				energy += node.getCurrentPower()
		print("FakeNetwork.updateNetwork() : nodes : ", energy)
		for node in self.network.getAll("solarpanel"):
			energy -= node.getCurrentPower()
		print("FakeNetwork.updateNetwork() : solarpanel : ", energy)
		for node in self.network.getAll("battery"):
			energy -= node.updateEnergy(energy, cycleDuration, now)
		print("FakeNetwork.updateNetwork() : battery : ", energy)
		publicpowergrid = self.network.getPublicpowergrid()
		if publicpowergrid:
			energy = publicpowergrid.updateEnergy(energy, cycleDuration)
		if energy!=0:
			energyKwh = energy*2.777e-7 # Convert Watt-second to Kilowatt-hour
			self.logger.error("Run out of energy of %s  kWh (%s ws) ",energyKwh, energy)
			raise DangerousStateException(
				f"Run out of energy of {energyKwh} kWh ({energy} ws)",
				"NOT_EQUILIBRATED_ELECTRIC_NETWORK"
			)
		return True
