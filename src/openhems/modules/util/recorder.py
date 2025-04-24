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
		def adaptDatetimeIso(val):
			"""Adapt datetime.datetime to timezone-naive ISO 8601 date."""
			print("adapt_datetime_iso(",val,") : ", val.isoformat())
			return val.isoformat()
		def convertDatetime(val):
			"""Convert ISO 8601 datetime to datetime.datetime object."""
			value = datetime.datetime.fromisoformat(val.decode())
			print("convert_datetime(",val,") : ", value)
			return value
		sqlite3.register_adapter(datetime.datetime, adaptDatetimeIso)
		sqlite3.register_converter("datetime", convertDatetime)


	def __del__(self):
		self.close()

	def getId(self):
		"""
		Return the nb call to newStep()
		Used to know how much cycle have been done so if EVAL mode end.
		"""
		return self._stepId

	def newStep(self, deviceId, stepType):
		"""
		Set the step of the recorder.
		"""
		self.deviceId = deviceId
		self.stepType = stepType
		self._stepId += 1

	def getDatas(self, deviceId, stepType):
		"""
		Query Sqlite3 for all 
		:return: Matrix of datas ordered by time. Each line correspond to a _stepId.
		"""
		self._cursor.execute(
			f"Select * from {self.tablename} where deviceId=? and stepType=? order by id",
			(deviceId, stepType))
		values = [] # List of record
		vals = [] # a record : List of tuples (time from start, sensor value)
		oldStep = 0
		initTime = 0
		while (row:=self._cursor.fetchone()) is not None:
			# logger.debug("Row: %s", row)
			_, deviceId, stepType, step, ts, sensorValue = row
			ts = datetime.datetime.fromisoformat(ts)
			if oldStep != step:
				initTime = ts
				oldStep = step
				if len(vals)>0:
					values.append(vals)
				vals = []
			timeValue = round((ts - initTime).total_seconds(),2)
			vals.append((timeValue, sensorValue))
		if len(vals)>0:
			values.append(vals)
		return values

	def connect(self):
		"""
		Connect to database if needed + create table
		"""
		if self._connection is None:
			# If done at __init__() it would have been done in a different thread (Error).
			self._connection = sqlite3.connect("openhems.db")
			if self.tablename is not None:
				self._cursor = self._connection.cursor()
				self.tablename = self.tablename
				self._cursor.execute(f"Create table if not exists {self.tablename} ("
					"id integer primary key,"
					"deviceId text,"
					"stepType text, step text,"
					"ts timestamp,"
					"value number(10))"
				)
				self._cursor.execute(
					f"CREATE INDEX if not exists getDatas ON {self.tablename} "
					"(deviceId, stepType)")
				# self._cursor.execute(f"Select count(*) from {self.tablename}")
				# row = self._cursor.fetchone()
				# self._count = row[0]
				self._cursor.execute(f"Delete from {self.tablename}")
				self.commit()

	def record(self, value, now=None):
		"""
		Record the sensor value in a database.
		"""
		if self._stepId==0:
			logger.debug("Do not record, _stepId==0.")
			return # deviceId/stepType are not set
		self.connect()
		if now is None:
			now = datetime.datetime.now()
		record = (self.deviceId, self.stepType, self._stepId, now, value)
		logger.debug("Register : %s", record)
		self._cursor.execute(
			f"Insert into {self.tablename} (deviceId, stepType, step, ts, value)"
			"values (?, ?, ?, ?, ?)", record)
		self.commit()
		self._count += 1
		# sql = f"Select * from {self.tablename} where deviceId=? and stepType=? and step=?"
		# self._cursor.execute(sql, (self.deviceId, self.stepType, self._stepId))
		# while (row:=self._cursor.fetchone()) is not None:
		# 	logger.debug("Row: %s", row)

	def commit(self):
		"""
		Sqlite3 commit
		"""
		if self._connection is not None:
			self._connection.commit()

	def close(self):
		"""
		Close the database connection.
		"""
		if self._connection is not None:
			self._connection.close()
			self._connection = None
