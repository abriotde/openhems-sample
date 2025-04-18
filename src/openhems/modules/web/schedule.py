"""
This class aim to comunicate what devices user want to schedule to the OpenHEMS core server.
The web server is the UI used to that.
"""
import logging
import datetime
from jinja2 import Template
from openhems.modules.util import CastUtililty, ConfigurationException

class OpenHEMSSchedule:
	"""
	This class aim to comunicate what devices user want to schedule to the OpenHEMS core server.
	 The web server is the UI used to that.
	"""
	duration: int = 0
	timeout = "00:00"
	def __init__(self, haId: str, name:str, node=None):
		self.name = name
		self.id = haId
		self.timeout:datetime = None
		self.duration:int = None
		self.logger = logging.getLogger(__name__)
		self.strategyCache = {}
		self._condition = None
		self.node = node

	def _getVal(self, haId):
		"""
		Method used when eval(_condition) to get HA value of an HA id.
		"""
		return self.node.network.networkUpdater.getEntityValue(haId)

	def setVal(self, haId, typename="str"):
		"""
		Method used with Jinja2 to register an HA id for later call _getVal().
		Like an __init__()
		"""
		if self.node is not None:
			self.node.network.networkUpdater.registerEntity(haId, typename)
			return "self._getVal('"+haId+"')"
		raise ConfigurationException(
			f"A node is necessary to register an HA id ({haId}, {typename})")

	def setCondition(self, condition):
		"""
		Set a condition to switch on device.
		Exp: "{{ getVal('sensor.carcharge') }}<80"
		"""
		if condition is not None:
			template = Template(condition)
			condition = template.render(getVal=self.setVal)
		self._condition = condition
		return self._condition

	def isScheduled(self):
		"""
		Return True, if device is schedule to be on
		"""
		try:
			# pylint: disable=eval-used
			if self._condition is not None and eval(self._condition):
				return True
		except NameError as e:
			self.logger.error("isScheduled(%s) = ERROR : %s : Ignore this condition.",
			                  self._condition, str(e))
			raise ConfigurationException(e) from e
		self.logger.debug("OpenHEMSSchedule.isScheduled(%s) : duration = %s",
				self.id, self.duration)
		return self.duration is not None and self.duration>0

	def setSchedule(self, duration:int=None, timeout:datetime=None):
		"""
		Set device duration to be on
		 AND timeout until witch all duration should be elapsed
		"""
		msg = ("OpenHEMSSchedule.setSchedule("
			f"{duration} seconds, timeout={timeout})")
		if duration is None:
			duration = self.duration
		if duration!=self.duration or self.timeout!=timeout:
			self.logger.info(msg)
		else:
			self.logger.debug("%s (no change)", msg)
		if timeout is not None and not isinstance(timeout, datetime.datetime):
			timeout = CastUtililty.toTypeDatetime(timeout)
		if not isinstance(duration, int):
			timeout = CastUtililty.toTypeInt(duration)
		self.duration = duration
		self.timeout = timeout
		self.strategyCache = {}

	def getStrategyCache(self, strategyId):
		"""
		Return cache used by a strategyId ()
		"""
		return self.strategyCache.get(strategyId, None)

	def setStrategyCache(self, strategyId, value):
		"""
		Set cache for a strategyId	
		"""
		self.strategyCache[strategyId] = value

	def decrementTime(self, duration):
		"""
		decrease time to be on from elapsed time.
		"""
		self.duration = max(self.duration-duration, 0)
		return self.duration

	def __json__(self, request=None):
		"""
		Export as JSON.
		"""
		del request
		timeout = self.timeout.strftime("%H:%M") if self.timeout is not None else "0"
		date = self.timeout.strftime("%d/%m/%Y") if self.timeout is not None else ""
		return {"name":self.name,
			"duration":self.duration,
			"timeout":timeout,
			"date":date}

	def __str__(self):
		timeout = self.timeout.strftime("%Y-%m-%d %H:%M:%S") if self.timeout is not None else "0"
		return f"Schedule({self.name}, duration:{self.duration}, timeout:{timeout})"
