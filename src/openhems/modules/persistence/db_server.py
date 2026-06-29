"""
This  implement a 'DB server'.
"""
import datetime
import json
from pathlib import Path
from openhems.modules.persistence import (
	SqliteRepository, NetworkSnapshot, EventDB, RecordDB
)
from openhems.modules.util import (
	json_default, ConfigurationManager
)

class OpenHEMSDBServer:
	"""
	This DB server do not run on its process but on core server one.
	  Core server call loop() at each of his loops.
	"""
	_INSTANCE = None
	@staticmethod
	def getInstance():
		"""
		Static access method.
		"""
		return OpenHEMSDBServer._INSTANCE

	def __init__(self, network, mylogger, serverConf: ConfigurationManager):
		self._network = network
		dbpath = serverConf.get("server.db.path", None)
		if dbpath is None:
			dbpath = str(Path(__file__).parent[0]/"data/openhems_db.sqlite")
		self._db = SqliteRepository(dbpath)
		self._loop_delay = serverConf.get("server.db.loop_delay", "int", defaultValue=120)
		self._now = None
		self.logger = mylogger
		self._cycle_id = 0
		self._events = []
		self._records = []
		self._is_on = True
		self._maxNbEvent = 100
		OpenHEMSDBServer._INSTANCE = self
	
	def loop(self, now=None):
		"""
		This will save in DB a snapshot of network 
		 and all events occured since last loop.
		"""
		self._cycle_id+=1
		if not self._is_on:
			self._events = []
			self._records = []
			return False
		if now is None:
			now = datetime.datetime.now()
		if self._now is None:
			loopDelay = 0
		else:
			loopDelay = now - self._now
			loopDelay = loopDelay.total_seconds()
			# print("loopDelay<self._loop_delay: ", loopDelay, self._loop_delay)
			if loopDelay<self._loop_delay:
				return False
		self._now = now
		network_json = json.dump(self._network, default=json_default)
		snapshot = NetworkSnapshot(self._cycle_id, now, network_json)
		self._db.save_snapshot(snapshot)
		for i, event in enumerate(self._events):
			# event_db = EventDB(self._cycle_id*self._maxNbEvent+i, now, network_json, event.type, event.device.getNameId(), event.action, event.source)
			self._db.save_event(event)
		for record in self._records:
			self._db.save_record(record)
		self._db.commit()
		return True

	def enable(self, is_on:bool):
		self._is_on = is_on

	def raise_event(self, event:EventDB):
		self._events.append(event)
		return True

	def record(self, event:RecordDB):
		self._records.append(event)
		return True

class Recorder():
	"""
	Recorder of a sensor value.
	Used on FeedbackSwitch.
	For exp: 
	  	Step 1 : Temperatre is 16°C inside, we switch on heater, until we reach 25°C.
		Step 2 : We switch off heater, temperature will raise 19°C
		Step 3 : Switch on heater
		...
		In each step, we store temperature every 30 seconds. So we have datas to infer informations.
		NB : It would be better to store too over parameters, outside temperature, humidity, day/night shift, sun luminancy...
		T(t) = Text + (T0 - Text) * e^(-t/τ)
		T(t) = T_eq + A₁ · e^(-t / τ₁) + A₂ · e^(-t / τ₂)
	"""

	def __init__(self, tablename=""):
		self._stepId = 0
		self.stepType = None
		self.deviceId = None
		self.tablename = tablename
		self._count = 0
		self._server = OpenHEMSDBServer.getInstance()


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
		self.deviceId = deviceId # Exp: mycar
		self.stepType = stepType # Exp: ON
		self._stepId += 1

	def getDatas(self, deviceId, stepType):
		"""
		Query Sqlite3 for all 
		:return: Matrix of datas ordered by time. Each line correspond to a _stepId.
		"""
		values = [] # List of record
		vals = [] # a record : List of tuples (time from start, sensor value)
		oldStep = 0
		initTime = 0
		for row in self._server._db.get_records(self.tablename, deviceId, stepType):
			# logger.debug("Row: %s", row)
			record:RecordDB = row
			if oldStep != record.step:
				initTime = record.timestamp
				oldStep = record.step
				if len(vals)>0:
					values.append(vals)
				vals = []
			timeValue = round((record.timestamp - initTime).total_seconds(),2)
			vals.append((timeValue, record.value))
		if len(vals)>0:
			values.append(vals)
		return values

	def connect(self):
		"""
		Connect to database if needed + create table
		"""
		pass

	def record(self, value, now=None):
		"""
		Record the sensor value in a database.
		"""
		if self._stepId==0:
			self._server.logger.debug("Do not record, _stepId==0.")
			return # deviceId/stepType are not set
		self.connect()
		if now is None:
			now = datetime.datetime.now()
		record = RecordDB(None, now, self.tablename, 
					self.deviceId, self.stepType, self._stepId, value)
		self._server.record(record)
		self._count += 1

	def commit(self):
		"""
		Sqlite3 commit
		"""
		pass

	def close(self):
		"""
		Close the database connection.
		"""
		pass
