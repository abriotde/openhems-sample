"""
Custom and specific time management for OpenHEMS
"""

import sqlite3
import datetime
import logging

logger = logging.getLogger(__name__)

class Recorder():
	"""
	Recorder of a sensor value.
	"""
	_INSTANCE = None
	@staticmethod
	def getInstance():
		"""
		Static access method.
		"""
		if Recorder._INSTANCE is None:
			Recorder._INSTANCE = Recorder()
		return Recorder._INSTANCE

	def __init__(self, tablename=None):
		self._connection = None
		self._cursor = None
		self._stepId = 0
		self.stepType = None
		self.deviceId = None
		self.tablename = tablename
		self._count = 0


	def __del__(self):
		self.close()

	def newStep(self, deviceId, stepType):
		"""
		Set the step of the recorder.
		"""
		self.deviceId = deviceId
		self.stepType = stepType
		self._stepId += 1

	def connect(self):
		if self._connection is None:
			# If done at __init__() it would have been done in a different thread (Error).
			self._connection = sqlite3.connect("openhems.db")
			if self.tablename is not None:
				self._cursor = self._connection.cursor()
				self.tablename = self.tablename
				self._cursor.execute(f"Create table if not exists {self.tablename} ("
					"i integer primary key,"
					"deviceId text,"
					"stepType text, step text,"
					"ts timestamp,"
					"value number(10))"
				)
				self._cursor.execute(f"Select count(*) from {self.tablename}")
				row = self._cursor.fetchone()
				self._count = row[0]

	def record(self, value):
		"""
		Record the sensor value in a database.
		"""
		self.connect()
		now = datetime.datetime.now()
		self._stepId += 1
		record = (self.deviceId, self.stepType, self._stepId, now, value)
		logger.debug("Register : %s", record)
		self._cursor.execute(f"Insert into {self.tablename} (deviceId, stepType, step, ts, value)"
				"values (?, ?, ?, ?, ?)", record
			)
		self.commit()
		self._count += 1
		self._cursor.execute(f"Select * from {self.tablename}")
		row=self._cursor.fetchone()
		while row is not None:
			print("Row:", row)
			row=self._cursor.fetchone()

	def commit(self):
		self._connection.commit()

	def close(self):
		"""
		Close the database connection.
		"""
		self._connection.close()
