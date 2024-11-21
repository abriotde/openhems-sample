"""
This module aim to delay some notification in order to group them
 to avoid to much similar notifications
"""

import datetime
import dataclasses
import logging
from itertools import islice
# import traceback

@dataclasses.dataclass
class MessageLog:
	"""
	Just to keep trace of logs, last notify() calls.
	We group them that's why there is count and interval
	"""
	date:datetime.datetime = None
	count:int = 1
	interval:datetime.timedelta = 1

class MessageHistory:
	"""
	Manage a message string repetition to avoid it's log repetition polution.
	"""
	COMPACT_SIZE = 8
	SILENCE_BEFORE_CLEAR = 5
	PURGE_HISTO_IN_DAY = datetime.timedelta(days=1)
	def __init__(self, message, manager):
		self.logs = []
		self.nextSize = self.COMPACT_SIZE # When reach that size, call compact()
		self.expectedSilence = self.SILENCE_BEFORE_CLEAR
		self.message = message
		self.manager = manager

	def compactLast(self):
		"""
		This will 
		"""
		size = len(self.logs)
		ok = False
		todo = True
		while size>=self.COMPACT_SIZE and todo:
			last = self.logs[size-1]
			first = self.logs[size-self.COMPACT_SIZE]
			if last.count==first.count:
				ok = True
				first.count *= self.COMPACT_SIZE
				first.interval = last.date-first.date
				first.date = last.date
				size -= self.COMPACT_SIZE-1
				self.logs = self.logs[:size]
			else:
				todo = False
				if not ok:
					self.manager.logger.debug("ERROR : NotificationManager.compactLast()"
						" last.count!=first.count : %d!=%d : d in(%d,%d) IN %s",
						last.count, first.count, size-1, size-self.COMPACT_SIZE-1,
						self.logs)
		return len(self.logs) # Safer than compute it

	def compact(self, now=None):
		"""
		Compact the log to know if ther is lots of messages.
		"""
		# self.manager.logger.debug("NotificationManager.compact(%s)", self.logs)
		size = self.compactLast()
		self.nextSize = size + self.COMPACT_SIZE
		if size==1:
			timer = None
			message = self.getMessage()
		else:
			if now is None:
				now = datetime.datetime.now()
			if self.logs[0].date+datetime.timedelta(days=1)<now:
				histo = now - self.PURGE_HISTO_IN_DAY
				self.purge(histo)
			timer = now+datetime.timedelta(minutes=self.expectedSilence)
			message = self.message
		self.manager.setTimer(message, timer)
		# self.manager.logger.debug("NotificationManager.compact() => %s", self.logs)

	def getMessage(self):
		"""
		Display message wich was waiting timer.
		"""
		count:int = 0
		first = self.logs[0].date.strftime("%Y-%m-%d %H:%M:%s")
		last = self.logs[len(self.logs)-1].date.strftime("%Y-%m-%d %H:%M:%s")
		for l in islice(self.logs, 1, None):
			count += l.count
		if count==0 and len(self.logs)==1:
			count = self.logs[0].count/self.COMPACT_SIZE*(self.COMPACT_SIZE-1)
			return f"\"{self.message}\" occured {int(count)} more times"
		return f"\"{self.message}\" occured {int(count)} times between {first} and {last}"

	def purge(self, histo, delete=False):
		"""
		Purge to 1 day.
		NB : For each 'log', date is the last occured, 
		but as we group by packet of power COMPACT_SIZE, There is always a level
		 we do not reach each day.
		For exp: If there id 100 messages per days and COMPACT_SIZE=10
		We should purge the day after we achive 100. I mean we have 200 in history max
		"""
		if delete:
			return self.logs[-1].date<histo
		if self.logs[0].date<histo:
			self.logs = list(filter(lambda x: x.date>histo, self.logs))
			return True
		return False

	def notify(self):
		"""
		Called when a new message occured:
		 Decide if we display it or not now
		"""
		now = datetime.datetime.now()
		self.logs.append( MessageLog(now, 1, 1) )
		size = len(self.logs)
		if size==1: # Case first message
			self.manager.setTimer(self.message)
		else:
			m0 = self.logs[size-2] # Previous message
			if m0.date+datetime.timedelta(minutes=self.expectedSilence)<now:
				self.manager.setTimer(self.message)
				self.expectedSilence = self.SILENCE_BEFORE_CLEAR
			if size>=self.nextSize:
				self.compact(now)
			else:
				timer = now+datetime.timedelta(minutes=self.expectedSilence)
				self.manager.setTimer(self.message, timer)
		# self.manager.logger.debug("NotificationManager.notify() => %s", self.logs)

class NotificationManager:
	"""
	This manage notification and choice when to print or to wait more.
	"""

	def __init__(self, networkUpdater, logger=None):
		self.networkUpdater = networkUpdater
		self.history = {}
		self.timers = {}
		self.sortedTimers = {}
		self.nextPurgeDate =  datetime.datetime.now() \
			 + MessageHistory.PURGE_HISTO_IN_DAY
		if logger is None:
			self.logger = logging.getLogger(__file__)
		else:
			self.logger = logger

	def setTimer(self, message, timer=None):
		"""
		The goal of this function is to delay a notification for a kind of message.
		 This delay will be checked on self.loop()
		"""
		self.logger.debug("setTimer(%s , %s)",message, timer)
		# for line in traceback.format_stack(): print(line)
		if timer is None:
			self.networkUpdater.notify(message)
		else:
			self.timers[message] = timer
			self.sortedTimers = None

	def loop(self, now=None):
		"""
		This function is call at each server loop and purge message in stack
		 when there is no more notifications during a time.
		 The stack was fill by self.setTimer()
		"""
		if now is None:
			now = datetime.datetime.now()
		# Refresh sortedTimers (A cache to improve next step)
		if self.sortedTimers is None and len(self.timers)>0:
			self.sortedTimers = sorted(self.timers.items(), key=lambda x: x[1])
		# emit all oldest timer wich need to be notify
		if self.sortedTimers is not None:
			i = 0
			for i,timer in enumerate(self.sortedTimers):
				if timer[1]<=now:
					message = self.networkUpdater.notify(
						self.history[timer[0]].getMessage()
					)
					del self.timers[message]
				else:
					break
			if i>0:
				self.sortedTimers = self.sortedTimers[i:]

		# Purge
		if self.nextPurgeDate<now:
			histo = now - MessageHistory.PURGE_HISTO_IN_DAY
			for message,elem in self.history.items():
				if elem.purge(histo, True):
					self.history.pop(message)
			self.nextPurgeDate =  now + MessageHistory.PURGE_HISTO_IN_DAY

	def notify(self, message):
		"""
		This is a wrapper of self.networkUpdater.notify()
		 wich can buffer them (delay and group them).
		"""
		history = self.history.get(message)
		self.logger.debug("notify(%s)",message)
		if history is None:
			self.logger.debug("1st notify(%s)",message)
			history = MessageHistory(message, self)
			self.history[message] = history
		history.notify()
