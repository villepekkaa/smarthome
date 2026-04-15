# SmartHome (RuuviTag -> MQTT -> SQLite -> API -> Dashboard)

SmartHome collects BLE telemetry from RuuviTags, publishes it to MQTT, stores it in SQLite, and serves data through a FastAPI API and browser dashboard.

## Quick Start

1. Create and activate a virtual environment.

```bash
python -m venv .venv

# fish
source .venv/bin/activate.fish

# bash/zsh
# source .venv/bin/activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Copy environment config.

```bash
cp .env.example .env
```

4. Run services in separate terminals.

```bash
./scripts/run_store.sh
./scripts/run_collector.sh
./scripts/run_api.sh
```

5. Open dashboard and API docs.

- Dashboard: http://127.0.0.1:8000/dashboard
- OpenAPI docs: http://127.0.0.1:8000/docs

## Data Flow

```text
RuuviTag BLE advertisements
   -> collector (Bleak)
   -> MQTT broker (Mosquitto)
   -> store service
   -> SQLite telemetry.db
   -> FastAPI routes/services
   -> Dashboard (/dashboard)
```

## Prerequisites

- Python 3.10+
- BLE-capable Bluetooth adapter
- MQTT broker (Mosquitto)

Linux (example):

```bash
sudo systemctl enable --now bluetooth
sudo systemctl enable --now mosquitto
```

## Configuration

Copy template:

```bash
cp .env.example .env
```

Example `.env`:

```env
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_TOPIC_PREFIX=home/ruuvi
MQTT_TOPIC=home/ruuvi/+/telemetry
ALLOWED_MACS=EA:10:CF:D3:59:AD,C7:EB:D8:F6:F0:19
DB_PATH=telemetry.db
API_HOST=0.0.0.0
API_PORT=8000
```

Notes:

- `ALLOWED_MACS` must be comma-separated, uppercase MACs with colons.
- If `ALLOWED_MACS` is empty, all Ruuvi tags are accepted.
- `DB_PATH` can be relative (project directory) or absolute.

## Run Services

Run each service in a separate terminal with the venv activated.

1. Store service (MQTT -> SQLite)

```bash
./scripts/run_store.sh
```

2. Collector service (BLE -> MQTT)

```bash
./scripts/run_collector.sh
```

3. API + dashboard

```bash
./scripts/run_api.sh
```

Legacy top-level files (`api.py`, `ruuvi_collector.py`, `ruuvi_store.py`) are compatibility wrappers.

## Verify Each Stage

1. Collector receives BLE advertisements.

- Look for collector logs and periodic stats lines.

2. Store receives and writes messages.

- Look for `Stored:` lines in the store terminal.

3. Database has telemetry rows.

```bash
sqlite3 telemetry.db "select id,sensor_id,iso_time,temperature_c,humidity_pct,battery_mv from telemetry order by id desc limit 10;"
```

4. API responds.

```bash
curl -s http://127.0.0.1:8000/health
curl -s "http://127.0.0.1:8000/latest"
```

## Troubleshooting

### Sensor updates are infrequent (stale values)

Common causes:

- Weak BLE reception (low RSSI)
- Physical distance or obstacles
- USB/Bluetooth adapter placement
- Host power saving affecting Bluetooth scanning

How to confirm packet loss:

- Compare sample counts per sensor in SQLite.
- Check `measurement_sequence` jumps for the affected sensor.

Example SQL checks:

```bash
sqlite3 telemetry.db "select sensor_id,count(*) from telemetry group by sensor_id;"
sqlite3 telemetry.db "select sensor_id,ts,rssi,measurement_sequence from telemetry where sensor_id='ruuvi_c7ebd8f6f019' order by id desc limit 20;"
```

What to try:

1. Move scanner host closer to the problematic tag.
2. Reposition adapter for better line-of-sight.
3. Verify tag battery/contact quality.
4. Keep collector running continuously and monitor stats output.

### Dashboard loads but no data

1. Confirm store service is running.
2. Confirm rows exist in `telemetry.db`.
3. Confirm API endpoint `/latest` returns items.

## Project Structure

```text
SmartHome/
   app/
      api/
         main.py
         routes/
            health.py
            sensors.py
            telemetry.py
            alerts.py
         services/
            telemetry_service.py
            alert_service.py
         db.py
         schemas.py
      collector/
         ruuvi_collector.py
         ruuvi_parser.py
         mqtt_publisher.py
      store/
         ruuvi_store.py
         repository.py
      web/
         templates/
            index.html
         static/
            css/
               dashboard.css
            js/
               dashboard.js
      config.py
   scripts/
      run_api.sh
      run_collector.sh
      run_store.sh
   tests/
```

## Development Notes

- API routing is in `app/api/routes`.
- DB query/business logic is in `app/api/services`.
- Store writes are centralized in `app/store/repository.py`.
- Frontend assets are under `app/web/static`.

## Security and Privacy

Do not commit:

- `.env`
- `telemetry.db`
- logs containing private location/device metadata