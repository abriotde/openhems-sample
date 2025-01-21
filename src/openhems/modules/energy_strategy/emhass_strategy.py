"""
This strategy use HEMASS to choose what to do.
This use Artificial Intelligence to guess the  futur.
So this require some more Python packages.
"""

import math
from datetime import datetime, timedelta
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

	def __init__(self, mylogger, network: OpenHEMSNetwork, configuration:ConfigurationManager,
	             strategyId:str="emhass"):
		super().__init__(strategyId, network, mylogger, True)
		self.adapter = EmhassAdapter.createFromOpenHEMS(configuration, network)
		self.logger.info("EmhassStrategy()")
		self.network = network
		freq = configuration.get("emhass.freq")
		self.emhassEvalFrequence = timedelta(minutes=freq)
		self.timezone = pytz.timezone(configuration.get("localization.timeZone"))
		self.data = None
		self.deferables = {}
		self.deferablesKeys = []
		self.nextEvalDate = datetime.now(self.timezone) - self.emhassEvalFrequence

	def emhassEval(self):
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
				for timestamp, row in self.data.iterrows():
					row = "> "+str(timestamp)
					for index, deferable in enumerate(self.deferablesKeys):
						key = 'P_deferrable'+str(index)
						row += ", "+deferable.node.id+"="+str(row[key])
					self.logger.debug(row)
		else:
			self.logger.debug("No deferrables so no EMHASS optimization to do.")
			data = None
		self.deferablesKeys = self.deferables.keys()
		self.data = data
		self.nextEvalDate = datetime.now(self.timezone) + self.emhassEvalFrequence
		return data

	def getDurationInHour(self, durationInSecs):
		"""
		Return duration in Emhass prevision granularity
		"""
		# TODO granularity can be less or more than hour...
		return math.ceil(durationInSecs / 3600)

	def updateDeferables(self):
		"""
		Update scheduled devices according to emhass
		 to scheduled devices according to openhems
		Return true if schedule has been updated
		"""
		# print("EmhassStrategy.updateDeferables()")
		update = False
		self.deferables = {}
		for node in self.network.getAll("out"):
			nodeId = node.id
			durationInSecs = node.getSchedule().duration
			deferable = self.deferables.get(nodeId, None)
			durationInHour = self.getDurationInHour(durationInSecs)
			if deferable is None:
				if durationInSecs>0: # Add a new deferrable
					update = True
					power = node.getMaxPower()
					self.deferables[nodeId] = Deferrable(
						power=power, duration=durationInHour, node=node
					)
			else:
				if durationInSecs<=0: # Remove a deferrable
					del self.deferables[nodeId]
					update = True
				elif deferable.duration!=durationInHour: # update a deferrable
					update = True
					deferable.duration = durationInHour
		print("EmhassStrategy.updateDeferables() => ", update, )
		return update

	def check(self, now=None):
		"""
		Check and eval if necessary
		- EMHASS optimization
		- power margin
		- conformity to EMHASS plan
		"""
		# print("EmhassStrategy.check()")
		if now is None:
			now = datetime.now(self.timezone)
		if self.updateDeferables() or now>self.nextEvalDate:
			# print("EmhassStrategy.check() : emhassEval")
			self.emhassEval()

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
		if self.data is None or isinstance(self.data, bool): # Case no deferables or Error
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
		for timestamp, row in self.data.iterrows():
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
		if not stop: # should be impossible : Relaunch emhassEval()?
			self.logger.error("No row in data previsions from EMHASS for current datetime.")
			return ((None, None, None), (None, None, None))
		return [[prevDT, curDT, nextDT], [prevRow, curRow, nextRow]]

	def emhassApply(self, cycleDuration, now=None):
		"""
		This should apply emhass result (emhassEval call) : self.data
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
			self.switchOnSchedulable(deferable.node, cycleDuration, doSwitchOn)
		return True

	def updateNetwork(self, cycleDuration, allowSleep:bool, now=None):
		"""
		Decide what to do during the cycle:
		 IF off-peak : switch on all
		 ELSE : Switch off all AND Sleep until off-peak
		Now is used to get a fake 
		"""
		if now is None:
			now = datetime.now(self.timezone)
		elif now.tzinfo is None or now.tzinfo!=self.timezone:
			now = now.replace(tzinfo=self.timezone)
		self.check(now)
		self.emhassApply(cycleDuration, now=now)
