
# migrations.py

SCHEMA = """

CREATE TABLE IF NOT EXISTS network_snapshot (
    id INTEGER PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    network_json TEXT NOT NULL

);

CREATE TABLE IF NOT EXISTS forecast (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    valid_from INTEGER NOT NULL,
    valid_to INTEGER NOT NULL,
    payload_json TEXT NOT NULL

);

CREATE TABLE IF NOT EXISTS optimization_run (
    id INTEGER PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    finished_at INTEGER NOT NULL,
    strategy TEXT NOT NULL,
    duration_ms INTEGER,
    score REAL
);

CREATE TABLE IF NOT EXISTS decision (
    id INTEGER PRIMARY KEY,
    optimization_id INTEGER,
    timestamp INTEGER NOT NULL,
    device TEXT,
    action TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS event (
    id INTEGER PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    event_type INTEGER NOT NULL,
    device: TEXT,
    action: TEXT,
    source: TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS record (
    id INTEGER PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    type TEXT NOT NULL,
    device: TEXT,
    subtype: TEXT,
    step: INTEGER,
    value: REAL
);

"""


def migrate(connection):

    connection.executescript(SCHEMA)

    connection.commit()


## Future improvements

# This is intentionally minimal. Once integrated into OpenHEMS, I would evolve it in the following directions:
# 
# * Replace `payload_json` and `network_json` strings with serialization helpers so domain objects (`Network`, forecasts, decisions) can be stored and restored transparently.
# * Add query methods such as `get_decisions(start, end)`, `get_forecasts(source)`, and `get_last_optimization()` to support the web interface.
# * Introduce a `SchemaVersion` table and incremental migrations (`V1`, `V2`, ...) instead of a single schema script, allowing the database to evolve without losing user data.
# * Add indexes on timestamps and foreign keys to keep history queries efficient as the database grows.
# * Implement retention policies (for example, keeping snapshots every minute for a week, then every hour for older data) to prevent unbounded growth.
# * Finally, expose this persistence layer through the web UI so users can inspect past optimizations, compare forecasts with actual values, and understand why OpenHEMS made each decision.
