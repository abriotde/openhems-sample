"""
This strategy use HEMASS to choose what to do.
This use Artificial Intelligence to guess the  futur.
So this require some more Python packages.

TODO : RunOk - InProd
"""

from datetime import datetime
import logging
import pytz
import numpy as np
from openhems.modules.network.network import OpenHEMSNetwork
from openhems.modules.util.configuration_manager import ConfigurationManager
from .energy_strategy import EnergyStrategy # , LOOP_DELAY_VIRTUAL
from .driver.emhass_adapter import (
	Deferrable,
	EmhassAdapter
)

# pylint: disable=broad-exception-raised
class EmhassStrategy(EnergyStrategy):
	"""
	This strategy use HEMASS to choose what to do.
	This use Artificial Intelligence to guess the  futur.
	So this require some more Python packages.
	"""

	def __init__(self, mylogger, network: OpenHEMSNetwork,
			configurationGlobal:ConfigurationManager, configurationEmhass:dict,
			strategyId:str="emhass"):
		freq = configurationEmhass.get("freq")
		super().__init__(strategyId, network, mylogger, evalFrequency=freq)
		self.logger.info("EmhassStrategy(%s)", configurationEmhass)
		self.adapter = EmhassAdapter.createFromOpenHEMS(
			configurationEmhass=configurationEmhass, configurationGlobal=configurationGlobal,
			network=network)
		self.network = network
		self.timezone = pytz.timezone(configurationGlobal.get("localization.timeZone"))
		self._data = None

	def eval(self):
		"""
		Launch EMHASS optimization plan and store result.
		Also update depending attributes.
		"""
		if len(self.deferables)>0:
			self.adapter.deferables = self.deferables.values()
			self.logger.info("EMHASS : Perform optimization.")
			data = self.adapter.performOptim()
			if self.logger.isEnabledFor(logging.DEBUG):
				self.logger.debug("EMHASS result is : %s", data)
				for timestamp, row in data.iterrows():
					row = "> "+str(timestamp)
					for index, deferable in enumerate(self.deferablesKeys):
						key = 'P_deferrable'+str(index)
						row += ", "+deferable.node.id+"="+str(row[key])
					self.logger.debug(row)
		else:
			self.logger.debug("No deferrables so no EMHASS optimization to do.")
			data = None
		self.deferablesKeys = self.deferables.keys()
		self._data = data
		return data

	def getDeferrables(self, node, durationInSecs):
		"""
		Return a Deferrable representing the node (adding usefull informations for algo).
		"""
		power = node.getMaxPower()
		return Deferrable(
			power=power, duration=durationInSecs, node=node
		)

	def evaluatePertinenceSwitchOn(self, switchOnRate, node):
		"""
		Convert a rate to a True/false choice.
		"""
		#TODO : Check power marrgin/respect of previsions...
		if switchOnRate==0 or node.getSchedule().duration<=0:
			return False
		isNodeOn = node.isOn()
		return switchOnRate>40 if isNodeOn else switchOnRate>50 # To avoid swapping

	def getRowsAt(self, now=None):
		"""
		Return a tuple of datetime and rows for datetime = "now", 
			with previous (If present) and Next one
		"""
		if self._data is None or isinstance(self._data, bool): # Case no deferables or Error
			return ((None, None, None), (None, None, None))
		if now is None:
			now = datetime.now(self.timezone)
		# Get row for current timestamp AND previous one and next one.
		prevRow = None
		curRow = None
		nextRow = None
		prevDT = None
		curDT = None
		nextDT = None
		stop = False
		for timestamp, row in self._data.iterrows():
			prevDT = curDT
			curDT = nextDT
			nextDT = timestamp.to_pydatetime()
			prevRow = curRow
			curRow = nextRow
			nextRow = row
			if stop: # We are in the right current time range. Keep the next one and exit.
				return ((prevDT, curDT, nextDT), (prevRow, curRow, nextRow))
			if nextDT>now:
				stop = True
		if not stop: # should be impossible : Relaunch eval()?
			self.logger.error("No row in data previsions from EMHASS for current datetime.")
			return ((None, None, None), (None, None, None))
		return [[prevDT, curDT, nextDT], [prevRow, curRow, nextRow]]

	def apply(self, cycleDuration, now=None):
		"""
		This should apply emhass result (eval call) : self._data
		"""
		if now is None:
			now = datetime.now(self.timezone)
		timestamp, rows = self.getRowsAt(now)
		if rows[1] is None: # Case no deferables
			self.network.switchOffAll()
			return True
		if rows[0] is None: # !!! But prevous row can be None !!!
			rows = (rows[1], rows[1]) # Do as Previous row confirm current row
			# (Rate = 100 before mid-hour)
		# Evaluate rate of correctness of each row.
		# If we are in the middle of current timestamp range keep it otherwise apply a rate
		# prevRate + curRate + nextRate allways = 1
		a = (now-timestamp[1]).total_seconds()
		duration = a+(timestamp[2]-now).total_seconds()
		rates = (max(duration-2*a, 0)/(2*duration),
				(duration + 2*min(a,(duration-a)))/(2*duration),
				max(duration-2*(duration-a), 0)/(2*duration))

		for index, deferableName in enumerate(self.deferablesKeys):
			vals = [row['P_deferrable'+str(index)] for row in rows]
			value = max(vals)
			if value == 0:
				switchOnRate = 0.0
			else:
				switchOnRate = 100 * ( np.dot(vals, rates) ) / value
			deferable = self.deferables[deferableName]
			doSwitchOn = self.evaluatePertinenceSwitchOn(switchOnRate, deferable.node)
			self.switchSchedulable(deferable.node, cycleDuration, doSwitchOn)
		return True
