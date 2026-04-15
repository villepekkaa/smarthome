import json
import sqlite3
from datetime import datetime


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    iso_time TEXT NOT NULL,
    topic TEXT NOT NULL,
    sensor_id TEXT NOT NULL,
    mac TEXT,
    name TEXT,
    rssi INTEGER,
    temperature_c REAL,
    humidity_pct REAL,
    pressure_pa REAL,
    battery_mv INTEGER,
    tx_power_dbm INTEGER,
    movement_counter INTEGER,
    measurement_sequence INTEGER,
    raw_json TEXT NOT NULL
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute(SCHEMA_SQL)
    conn.commit()
    return conn


def insert_telemetry(conn: sqlite3.Connection, topic: str, payload: dict) -> None:
    values = payload.get("values", {})
    ts = int(payload.get("ts", 0))
    iso_time = datetime.utcfromtimestamp(ts).isoformat() + "Z" if ts else ""

    conn.execute(
        """
        INSERT INTO telemetry (
            ts, iso_time, topic, sensor_id, mac, name, rssi,
            temperature_c, humidity_pct, pressure_pa, battery_mv,
            tx_power_dbm, movement_counter, measurement_sequence, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ts,
            iso_time,
            topic,
            payload.get("sensor_id"),
            payload.get("mac"),
            payload.get("name"),
            payload.get("rssi"),
            values.get("temperature_c"),
            values.get("humidity_pct"),
            values.get("pressure_pa"),
            values.get("battery_mv"),
            values.get("tx_power_dbm"),
            values.get("movement_counter"),
            values.get("measurement_sequence"),
            json.dumps(payload),
        ),
    )
    conn.commit()
