"""
This Feeder aim to abstract the update of a value using the NetworkUpdater.
For the Network, we always "getValue" but when it's a dynamic value, 
the NetworkUpdater will really search to update the value. 
"""

import random
# import logging
import math
import pytz
import pvlib
import pandas as pd
from openhems.modules.util import CastUtililty
# from .homestate_updater import HomeStateUpdater

# pylint: disable=too-few-public-methods
class Feeder:
	"""
	Abstract class to reprensent the concept:
	This Feeder aim to abstract the update of a value using the NetworkUpdater.
	For the Network, we always "getValue" but when it's a dynamic value, 
	the NetworkUpdater will really search to update the value.
	For exemple : The maximum power we can give can be constant (From the grid)
	 or variable like form battery/solar-panel.
	But sometime, it's just because we do not have a sensor for this, 
	so we use const value as "patch".
	"""
	def __init__(self, value=None):
		self.value = value

	def getValue(self):
		"""
		Return Value. Ths is default implementation
		"""
		return self.value

# pylint: disable=too-few-public-methods
class SourceFeeder(Feeder):
	"""
	Get value from Network.
	:source HomeStateUpdater: The source of the value
	:typename str: The name of the expected type
	"""
	def __init__(self, nameid, source, typename:str):
		super().__init__()
		self.nameid = nameid
		self.source = source
		self.source.registerEntity(nameid, typename)
		self.sourceId = -100 # For cache : Warning must be <0 : HomeStateUpdater start at 0

	def getValue(self):
		"""
		getValue from the "source" if source.id has been updated.
		"""
		# Check if need to update SourceFeeder cache
		sourceId = self.source.getCycleId()
		if self.sourceId<sourceId:
			# Better to update sourceId before in case value is
			# updated between the 2 next lines
			self.sourceId = sourceId
			self.value = self.source.getEntityValue(self.nameid)
		return self.value

	def __str__(self):
		return "SourceFeeder("+self.nameid+")"

# pylint: disable=too-few-public-methods
class ConstFeeder(Feeder):
	"""
	This is for value wich are constant.
	"""
	def __init__(self, value, nameid=None, expectedType=None):
		if expectedType is not None:
			value = CastUtililty.toType(expectedType, value)
		super().__init__(value)
		if nameid is None:
			nameid = str(value)
		self.nameid = nameid
	def __str__(self):
		return f"ConstFeeder({self.value})"

class RandomFeeder(Feeder):
	"""
	The return 'value' is a random value between a 'minimum' and 'maximum',
	 but on each openHEMS cycles it does not change a lot usualy.
	The evolution is quite slow witch is more realistic.
	"""
	def __init__(self, source, minimum, maximum, averageStep=None):
		super().__init__((minimum + maximum) / 2)
		self.source = source
		self.min = minimum
		self.max = maximum
		if averageStep is None:
			averageStep = (maximum - minimum)/10
		self.avgStep = averageStep
		self.lastRefreshId = self.source.getCycleId()-1

	def getValue(self):
		"""
		The return 'value' is a random value between a 'minimum' and 'maximum',
		But each step is a gaussian step between the current value.
		"""
		if self.lastRefreshId < self.source.getCycleId():
			self.value = min(max(
					self.value + random.gauss(0, 2*self.avgStep),
				self.min), self.max)
		return self.value
	def __str__(self):
		return "RandomFeeder("+str(self.min)+", "+str(self.max)+")"

class RotationFeeder(Feeder):
	"""
	The return 'value' rotate on a list of predefined 'values'.
	It can be usefull to simulate a cylcle or random but with predicaled values
	 (Usefull for tests)
	"""
	def __init__(self, source, valuesList:list):
		self.len = len(valuesList)
		if self.len==0:
			# logger.error("RotationFeeder() init with empty list. Sert to default [0]")
			valuesList = [0]
			self.len = len(valuesList)
		super().__init__(valuesList[0])
		self.values = valuesList
		self.source = source

	def getValue(self):
		"""
		The return 'value' rotate on a list of predefined 'values'.
		On each OpenHEMS server loop, self.source.cylceId should increment,
		 witch occure the change, 
		"""
		i = self.source.getCycleId() % self.len
		return self.values[i]
	def __str__(self):
		return "RotationFeeder("+str(self.values)+")"

class StateFeeder(ConstFeeder):
	"""
	This is a state machine : This value is the one set before.
	(Like a ConstFeeder that we can change)
	"""

	def setValue(self, value):
		"""
		Change the value to new one.
		"""
		self.value = value
	def __str__(self):
		return "StateFeeder("+str(self.value)+")"

class FakeSwitchFeeder(Feeder):
	"""
	The return 'value' rotate on a list of predefined 'values'.
	It can be usefull to simulate a cylcle or random but with predicaled values
	 (Usefull for tests)
	"""
	def __init__(self, source:Feeder, isOn:Feeder, defaultValue=0):
		super().__init__(source)
		self.isOn = isOn
		self.defaultValue = defaultValue

	def getValue(self):
		"""
		The return 'value' rotate on a list of predefined 'values'.
		On each OpenHEMS server loop, self.source.cycleId should increment,
		 witch occure the change, 
		"""
		if self.isOn.getValue():
			return self.value.getValue()
		return self.defaultValue
	def __str__(self):
		return f"FakeSwitchFeeder({self.defaultValue})"

class SumFeeder(Feeder):
	"""
	The return 'value' whitch is the sum of getNodes()
	"""
	def __init__(self, network, inputType="out"):
		super().__init__(inputType.lower())
		self._network = network

	def getValue(self):
		"""
		The return 'value' rotate on a list of predefined 'values'.
		On each OpenHEMS server loop, self.source.cycleId should increment,
		 witch occure the change, 
		"""
		mysum = sum(
			node.getCurrentPower()
			for node in self._network.getAll(self.value))
		return mysum

	def __str__(self):
		return f"SumFeeder({self.value})"

# pylint: disable=invalid-name

class SolarFeeder(Feeder):
	"""
	It's tosimulate a solar panel.

	randomizeFactor: Factor between 0 and 1. 
	This simulate weather conditions: higher value, 
	mean more chances the power received is diminished.
	"""
	def __init__(self, network, nb_panel:int=10, azimuth:float=180, randomizeFactor:float=0.0):
		super().__init__(None)
		self._network = network
		self._nb_panel = nb_panel
		self._azimuth = azimuth
		self._random = randomizeFactor

	def getValue(self):
		"""
		The return 'value' rotate on a list of predefined 'values'.
		On each OpenHEMS server loop, self.source.cycleId should increment,
		 witch occure the change, 
		"""
		time = self._network.getTime()
		# utc_time = tz.localize(time).astimezone(pytz.utc)
		lon, lat, alt = 48.435, -2.201, 100 # (Longitude, Latitude, Altitude)
		times = pd.DatetimeIndex(
			[time],
			tz=pytz.timezone('Europe/Paris')
		)
		panel_area = 1.7 * self._nb_panel
		panel_efficiency = 0.20
		surface_tilt = lat # use evaluate_tilt() ?
		surface_azimuth = self._azimuth
		# mc = pvlib.modelchain.ModelChain.with_basic_chain(
		# 	latitude=lat,
		# 	longitude=lon,
		# 	altitude=alt,
		# 	surface_tilt=surface_tilt,
		# 	surface_azimuth=surface_azimuth,
		# )
		solar_position = pvlib.solarposition.get_solarposition(times, lat, lon, altitude=alt)
		clearsky = pvlib.clearsky.ineichen(times, lat, lon, altitude=alt)
		tilted_irradiance = pvlib.irradiance.get_total_irradiance(
			surface_tilt=surface_tilt,
			surface_azimuth=surface_azimuth,
			solar_zenith=solar_position['apparent_zenith'],
			solar_azimuth=solar_position['azimuth'],
			dni=clearsky['dni'],
			ghi=clearsky['ghi'],
			dhi=clearsky['dhi'],
			model='haydavies'
		)
		power_received = tilted_irradiance['poa_global'] * panel_area * panel_efficiency
		if self._random != 0.0:
			# lower is _random, more chances is power_received less diminished
			power_received *= math.pow(random.uniform(0, 1), self._random)
		return power_received

	def __str__(self):
		return f"SolarFeeder(nb={self._nb_panel}, azimuth={self._azimuth}, rand={self._random})"


# def evaluate_tilt(tilt, panel_azimuth, solar_pos, clearsky, weight_type='flat_curve'):
# 	"""
# 	Calculates the weighted value of a given tilt.
# 	weight_type: 'flat_curve' or 'peak_shaving'
# 	"""
# 	tilted = pvlib.irradiance.get_total_irradiance(
# 	    surface_tilt=tilt,
# 	    surface_azimuth=panel_azimuth,
# 	    solar_zenith=solar_pos['apparent_zenith'],
# 	    solar_azimuth=solar_pos['azimuth'],
# 	    dni=clearsky['dni'],
# 	    ghi=clearsky['ghi'],
# 	    dhi=clearsky['dhi'],
# 	    model='haydavies'
# 	)
# 	times = pd.date_range(start='2026-01-01', end='2027-01-01', freq='60T', tz='UTC')
#
# 	# Get hourly POA (Plane of Array) irradiance in W/m²
# 	poa_hourly = tilted['poa_global']
#
# 	# Convert index to local solar time for weighting (approximate)
# 	# We will just extract the hour-of-day (UTC + offset)
# 	# For Beijing, UTC+8 gives local time.
# 	local_hours = (times.hour + 8) % 24  # Simple local hour (DST ignored, good enough)
#
# 	# Give high value to morning (6-9 AM) and evening (3-6 PM)
# 	# Give lower value to midday (10 AM - 2 PM) to flatten the peak.
# 	weights = np.ones(len(local_hours)) * 0.5  # Base weight
# 	weights[(local_hours >= 3) & (local_hours < 9)] = 1.5   # Morning peak
# 	weights[(local_hours >= 15) & (local_hours < 21)] = 1.5 # Evening peak
# 	weights[(local_hours >= 9) & (local_hours < 15)] = 0.8  # Midday (lower importance)
# 	weights[local_hours < 3] = 0   # Night
# 	weights[local_hours >= 21] = 0 # Night
# 	# Calculate weighted sum (in Wh/m²)
# 	weighted_sum = (poa_hourly * weights).sum()
# 	return weighted_sum
