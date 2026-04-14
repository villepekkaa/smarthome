# SmartHome (RuuviTag -> MQTT -> SQLite -> API -> Dashboard)

This project collects real BLE telemetry from RuuviTags, publishes it to MQTT, stores it in SQLite, and exposes it via a FastAPI backend + browser dashboard.

## Current architecture

1. `ruuvi_collector.py`
   - Scans BLE advertisements
   - Parses Ruuvi RAWv2 payload
   - Publishes JSON to MQTT topic:
     - `home/ruuvi/<sensor_id>/telemetry`

2. `ruuvi_store.py`
   - Subscribes to MQTT topic:
     - `home/ruuvi/+/telemetry`
   - Stores telemetry rows into SQLite (`telemetry.db`)

3. `api.py`
   - Reads telemetry from SQLite
   - Exposes endpoints:
     - `/health`
     - `/sensors`
     - `/latest`
     - `/history`
     - `/alerts`
     - `/alert-summary`

4. `dashboard.html`
   - Shows latest sensor cards
   - History chart (temp/humidity)
   - Alert summary and active alerts

---

## Requirements

- Python 3.10+ (3.11+ recommended)
- BLE-capable Bluetooth adapter
- MQTT broker (Mosquitto)

### OS support
- Linux: tested (CachyOS/Arch)
- Windows: supported with BLE + Mosquitto setup
- macOS: likely works with same Python dependencies

---

## Install

### Linux (CachyOS/Arch)
```bash
sudo pacman -Syu bluez bluez-utils mosquitto python python-pip sqlite
sudo systemctl enable --now bluetooth
sudo systemctl enable --now mosquitto
```

### Python environment
```bash
python -m venv .venv
# fish:
source .venv/bin/activate.fish
# bash/zsh:
# source .venv/bin/activate
pip install bleak paho-mqtt python-dotenv fastapi uvicorn
```

---

## Configuration

Copy template:
```bash
cp .env.example .env
```

Edit `.env` values:
- `MQTT_HOST`
- `MQTT_PORT`
- `MQTT_TOPIC_PREFIX`
- `MQTT_TOPIC`
- `ALLOWED_MACS` (optional, comma-separated)
- `DB_PATH`

Example:
```env
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_TOPIC_PREFIX=home/ruuvi
MQTT_TOPIC=home/ruuvi/+/telemetry
ALLOWED_MACS=EA:10:CF:D3:59:AD,C7:EB:D8:F6:F0:19
DB_PATH=telemetry.db
```

---

## Run

Use separate terminals.

### 1) Store service (MQTT -> SQLite)
```bash
source .venv/bin/activate.fish
python ruuvi_store.py
```

### 2) Collector service (BLE -> MQTT)
```bash
source .venv/bin/activate.fish
python ruuvi_collector.py
```

### 3) API
```bash
source .venv/bin/activate.fish
python api.py
```

### 4) Dashboard
```bash
python -m http.server 8081
```
Open:
- `http://127.0.0.1:8081/dashboard.html`
- API docs: `http://127.0.0.1:8000/docs`

---

## Verify data

```bash
sqlite3 telemetry.db "select id,sensor_id,iso_time,temperature_c,humidity_pct,battery_mv from telemetry order by id desc limit 10;"
```

---

## Privacy / security

Do not commit:
- `.env`
- `telemetry.db`
- logs with private sensor/location metadata

Keep real MAC addresses and any credentials only in `.env`.

---

## Roadmap (next refactor)

Current code is intentionally functional-first and monolithic. Next step is to split into modules:

- `app/api/routes/*` (endpoint modules)
- `app/api/services/*` (DB query + alert logic)
- `app/web/static/js`, `app/web/static/css` (dashboard assets)
- shared `config.py` and `db.py`

This keeps behavior the same but makes the project production-like and easier to maintain.