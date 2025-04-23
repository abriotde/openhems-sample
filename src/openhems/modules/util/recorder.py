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

	def __init__(self, tablename=None, step=None):
		self.con = sqlite3.connect("openhems.db")
		self.step = step
		if tablename is not None:
			self.cur = self.con.cursor()
			self.tablename = tablename
			self.cur.execute(f"Create table if not exists {tablename} ("
				"i integer primary key,"
				"deviceId text,"
				"stepType text, step text,"
				"ts timestamp,"
				"value number(10))"
			)

	def __del__(self):
		self.close()

	def setStep(self, deviceId, stepType, step):
		"""
		Set the step of the recorder.
		"""
		self.deviceId = deviceId
		self.stepType = stepType
		self.step = step

	def record(self, value):
		"""
		Record the sensor value in a database.
		"""
		if self.step is not None:
			now = datetime.datetime.now()
			record = (self.deviceId, self.stepType, self.step, now, value)
			logger.debug("Register : %s", record)
			self.cur.execute(f"Insert into {self.tablename} (deviceId, stepType, step, ts, value)"
					"values (?, ?, ?, ?, ?)", record
				)
			self.con.commit()

	def close(self):
		"""
		Close the database connection.
		"""
		self.con.close()