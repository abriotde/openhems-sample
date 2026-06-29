
import sqlite3

import datetime
from .models import *
from .repository import Repository

class WrongSqlType(Exception):
    pass

class SqliteIterator:
    """
    Used to iterate over rows
    """
    def __init__(self, cursor, type):
        self._cursor = cursor
        self._type = type

    def __iter__(self):
        return self

    def __next__(self):
        """
        Return next item. Use it after get_records() in while.
        """
        row = self._cursor.fetchone()
        if row:
            if self._type==RecordDB:
                id, timestamp, type, device, subtype, step, value = row
                return RecordDB(id, timestamp, type, device, subtype, step, value)
            else:
                raise WrongSqlType(f"Unknown Iteratortype : ", self._type)
        else:
            raise StopIteration

class SqliteRepository(Repository):

    def __init__(self, filename: str = "openhems.sqlite3"):
        def datetime2DB(val:datetime):
            """Adapt datetime.datetime to timezone-naive ISO 8601 date."""
            ret = val.timestamp()
            print("datetime2DB(",val,") : ", ret)
            return ret
        def db2Datetime(val):
            """Convert ISO 8601 datetime to datetime.datetime object."""
            ret = datetime.fromtimestamp(val)
            print("db2Datetime(",val,") : ", ret)
            return ret
        sqlite3.register_adapter(datetime, datetime2DB)
        sqlite3.register_converter("datetime", db2Datetime)
        self.connection:sqlite3.Connection = sqlite3.connect(filename)
        self.connection.row_factory = sqlite3.Row
        self._cursor = None

    def save_snapshot(self, snapshot):
        self.connection.execute(
            """
            INSERT INTO network_snapshot
            (timestamp, network_json)
            VALUES (?, ?)
            """,
            (
                int(snapshot.timestamp.timestamp()),
                snapshot.network_json,
            ),
        )

    def commit(self):
        self.connection.commit()

    def save_event(self, event:EventDB):
        self.connection.execute(
            """
            INSERT INTO event
            (timestamp, event_type, device, action, source, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(event.timestamp.timestamp()),
                event.type.value,
                event.device,
                event.action,
                event.source,
                event.reason,
            ),
        )

    def save_record(self, record):
        self.connection.execute(
            """
            INSERT INTO record
            (timestamp, type, device, subtype, step, value)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(record.timestamp.timestamp()),
                record.type,
                record.device,
                record.subtype,
                record.step,
                record.value
            ),
        )

    def get_records(self, type, device, subtype=None):
        cursor = self.connection.cursor()
        cursor.execute(
            f"Select * from record where type=? and device=? and subtype=? order by id",
            (type, device, subtype))
        return SqliteIterator(cursor, RecordDB)


    def save_forecast(self, forecast):
        self.connection.execute(
            """
            INSERT INTO forecast
            VALUES (NULL, ?, ?, ?, ?, ?)
            """,
            (
                forecast.source,
                forecast.created_at.isoformat(),
                forecast.valid_from.isoformat(),
                forecast.valid_to.isoformat(),
                forecast.payload_json,
            ),
        )

    def save_optimization(self, optimization):

        cursor = self.connection.execute(
            """
            INSERT INTO optimization_run
            VALUES (NULL, ?, ?, ?, ?, ?)
            """,
            (
                optimization.started_at.isoformat(),
                optimization.finished_at.isoformat(),
                optimization.strategy,
                optimization.duration_ms,
                optimization.score,
            ),
        )
        self.connection.commit()
        return cursor.lastrowid
