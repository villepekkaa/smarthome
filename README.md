# SmartHome (RuuviTag -> MQTT -> SQLite)

Collect real BLE telemetry from RuuviTags, publish it to MQTT, and store it into SQLite for later analysis.

## Overview

Pipeline:

1. `ruuvi_collector.py` scans BLE advertisements and parses Ruuvi RAWv2 payloads.
2. Collector publishes telemetry JSON to MQTT topic:
   - `home/ruuvi/<sensor_id>/telemetry`
3. `ruuvi_store.py` subscribes to MQTT and stores events in `telemetry.db`.

This project is intentionally lightweight and local-first.

---

## Requirements

- Linux (tested on CachyOS / Arch-based distros)
- Python 3.11+
- Bluetooth adapter
- Mosquitto MQTT broker

---

## Install

### 1) System dependencies

```bash
sudo pacman -Syu bluez bluez-utils mosquitto python python-pip sqlite
sudo systemctl enable --now bluetooth
sudo systemctl enable --now mosquitto
```

### 2) Python virtual environment

```bash
python -m venv .venv
```

Activate:

```bash
# fish shell
source .venv/bin/activate.fish

# bash/zsh (alternative)
# source .venv/bin/activate
```

Install Python packages:

```bash
pip install bleak paho-mqtt python-dotenv
```

---

## Configuration

Create local config file from template:

```bash
cp .env.example .env
```

Edit `.env` with your local values:

- `MQTT_HOST` (default: `localhost`)
- `MQTT_PORT` (default: `1883`)
- `MQTT_TOPIC_PREFIX` (default: `home/ruuvi`)
- `MQTT_TOPIC` (default: `home/ruuvi/+/telemetry`)
- `ALLOWED_MACS` (comma-separated MAC list, optional)
- `DB_PATH` (default: `telemetry.db`)

Example:

```env
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_TOPIC_PREFIX=home/ruuvi
MQTT_TOPIC=home/ruuvi/+/telemetry
ALLOWED_MACS=EA:10:CF:D3:59:AD,C7:EB:D8:F6:F0:19
DB_PATH=telemetry.db
```

Notes:
- If `ALLOWED_MACS` is empty, collector accepts all detected Ruuvi tags.
- Keep real MAC addresses only in `.env`.

---

## Run

Use two terminals.

### Terminal A: MQTT -> SQLite consumer

```bash
source .venv/bin/activate.fish
python ruuvi_store.py
```

Expected behavior:
- Connects to MQTT broker
- Subscribes to `home/ruuvi/+/telemetry`
- Stores rows into `telemetry.db`

### Terminal B: BLE -> MQTT collector

```bash
source .venv/bin/activate.fish
python ruuvi_collector.py
```

Expected behavior:
- Scans BLE advertisements
- Parses Ruuvi payloads
- Publishes telemetry JSON to MQTT topics

---

## Verify data

Show latest rows:

```bash
sqlite3 telemetry.db "select id,sensor_id,iso_time,temperature_c,humidity_pct,pressure_pa,battery_mv from telemetry order by id desc limit 10;"
```

Count rows:

```bash
sqlite3 telemetry.db "select count(*) from telemetry;"
```

Latest timestamp per sensor:

```bash
sqlite3 telemetry.db "select sensor_id,max(ts) as last_ts from telemetry group by sensor_id;"
```

---

## MQTT payload format (example)

```json
{
  "sensor_id": "ruuvi_c7ebd8f6f019",
  "mac": "C7:EB:D8:F6:F0:19",
  "name": "Ruuvi F019",
  "ts": 1776065479,
  "rssi": -73,
  "values": {
    "temperature_c": 8.045,
    "humidity_pct": 52.225,
    "pressure_pa": 102804,
    "accel_x_mg": 16,
    "accel_y_mg": 16,
    "accel_z_mg": 1020,
    "battery_mv": 2907,
    "tx_power_dbm": 4,
    "movement_counter": 41,
    "measurement_sequence": 44793
  }
}
```

---

## Project files

- `ruuvi_collector.py` — BLE scanner + Ruuvi parser + MQTT publisher
- `ruuvi_store.py` — MQTT subscriber + SQLite writer
- `.env.example` — safe template config
- `.gitignore` — excludes local data/secrets
- `telemetry.db` — local SQLite database (generated at runtime)

---

## Privacy and security

Do not commit:

- `.env`
- `telemetry.db`
- logs that contain private location/device metadata

Recommended:
- Keep credentials and real device MACs only in `.env`
- Commit `.env.example` with placeholder values

---

## Troubleshooting

### Error: `await outside async function`
Check `ruuvi_collector.py` indentation:
- `async def main():` must exist
- `await scanner.start()` and `await scanner.stop()` must be inside `main()`

### No BLE data found
```bash
systemctl status bluetooth --no-pager
bluetoothctl scan on
```

### No MQTT messages
```bash
systemctl status mosquitto --no-pager
mosquitto_sub -h localhost -t 'home/ruuvi/#' -v
```

### Works with `sudo` only
If scanner works only as root, adjust local Bluetooth permissions/groups on your system.