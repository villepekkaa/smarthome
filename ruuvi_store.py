import json
import sqlite3
from datetime import datetime
import paho.mqtt.client as mqtt

DB_PATH = "telemetry.db"
TOPIC = "home/ruuvi/+/telemetry"

schema_sql = """
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

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute(schema_sql)
conn.commit()

def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected, subscribing:", TOPIC)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode("utf-8"))
    v = payload.get("values", {})
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
            ts, iso_time, msg.topic, payload.get("sensor_id"), payload.get("mac"),
            payload.get("name"), payload.get("rssi"),
            v.get("temperature_c"), v.get("humidity_pct"), v.get("pressure_pa"),
            v.get("battery_mv"), v.get("tx_power_dbm"),
            v.get("movement_counter"), v.get("measurement_sequence"),
            json.dumps(payload),
        ),
    )
    conn.commit()
    print("Stored:", payload.get("sensor_id"), iso_time, v.get("temperature_c"))

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.loop_forever()
