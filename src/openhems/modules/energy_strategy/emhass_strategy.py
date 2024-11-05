"""
This strategy use HEMASS to choose what to do.
This use Artificial Intelligence to guess the  futur.
So this require some more Python packages.
"""

import math
from datetime import datetime, timedelta
import logging
import numpy as np
from openhems.modules.network.network import OpenHEMSNetwork
from .energy_strategy import EnergyStrategy # , LOOP_DELAY_VIRTUAL
from .driver.emhass_adapter import (
	Deferrable,
	EmhassAdapter
)

# Time to wait in seconds before considering to be in offpeak range
TIME_MARGIN_IN_S = 1

# pylint: disable=broad-exception-raised
class EmhassStrategy(EnergyStrategy):
	"""
	This strategy use HEMASS to choose what to do.
	This use Artificial Intelligence to guess the  futur.
	So this require some more Python packages.
	"""

	def __init__(self, network: OpenHEMSNetwork, emhassFrequenceInMinutes=60):
		super().__init__()
		self.adapter = EmhassAdapter.createForOpenHEMS()
		self.logger.info("EmhassStrategy(%s)", str(emhassFrequenceInMinutes))
		self.network = network
		self.emhassEvalFrequence = timedelta(minutes=emhassFrequenceInMinutes)
		self.data = None
		self.deferables = {}
		self.deferablesKeys = []
		self.nextEvalDate = datetime.now() - self.emhassEvalFrequence

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
		self.nextEvalDate = datetime.now() + self.emhassEvalFrequence
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
		deferables = {}
		for node in self.network.out:
			nodeId = node.id
			durationInSecs = node.getSchedule().duration
			deferable = self.deferables.get(nodeId, None)
			durationInHour = self.getDurationInHour(durationInSecs)
			if deferable is None:
				if durationInSecs>0: # Add a new deferrable
					update = True
					power = node.getCurrentMaxPower()
					deferables[nodeId] = Deferrable(
						power=power, duration=durationInHour, node=node
					)
			else:
				if durationInSecs<=0: # Remove a deferrable
					del deferables[nodeId]
					update = True
				elif deferable.duration!=durationInHour: # update a deferrable
					update = True
					deferable.duration = durationInHour
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
			now = datetime.now()
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
		if self.data is None: # Case no deferables
			return ((None, None, None), (None, None, None))
		if now is None:
			now = datetime.now()
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
		return ([prevDT, curDT, nextDT], [prevRow, curRow, nextRow])

	def emhassApply(self, cycleDuration, now=None):
		"""
		This should apply emhass result (emhassEval call) : self.data
		"""
		if now is None:
			now = datetime.now()
		timestamp, rows = self.getRowsAt(now)
		if rows[1] is None: # Case no deferables
			self.network.switchOffAll()
			return True
		if rows[0] is None: # !!! But prevous row can be None !!!
			rows[0] = rows[1] # Do as Previous row confirm current row
			# (Rate = 100 before mid-hour)
		# Evaluate rate of correctness of each row.
		# If we are in the middle of current timestamp range keep it otherwise apply a rate
		# prevRate + curRate + nextRate allways = 1
		a = (now-timestamp[1]).total_seconds()
		duration = a+(timestamp[2]-now).total_seconds()
		rates = (max(duration-2*a, 0)/(2*duration),
				(duration + 2*min(a,(duration-a)))/(2*duration),
				max(duration-2*(duration-a), 0)/(2*duration))

		for index, deferable in enumerate(self.deferablesKeys):
			key = 'P_deferrable'+str(index)
			vals = [row[key] for row in rows]
			value = max(vals)
			switchOnRate = 0.0
			if value == 0:
				switchOnRate = 0.0
			else:
				switchOnRate = 100 * ( np.dot(vals, rates) ) / value
			doSwitchOn = self.evaluatePertinenceSwitchOn(switchOnRate, deferable.node)
			self.switchOn(deferable.node, cycleDuration, doSwitchOn)
		return True

	def updateNetwork(self, cycleDuration, now=None):
		"""
		Decide what to do during the cycle:
		 IF off-peak : switch on all
		 ELSE : Switch off all AND Sleep until off-peak
		Now is used to get a fake 
		"""
		if now is None:
			now = datetime.now()
		self.check(now)
		self.emhassApply(cycleDuration, now=now)
