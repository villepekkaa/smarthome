# SmartHome (RuuviTag -> MQTT -> SQLite -> API -> Dashboard)

This project collects BLE telemetry from RuuviTags, publishes it to MQTT, stores it in SQLite, and serves telemetry + dashboard via FastAPI.

## Project structure

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

Legacy top-level files (`api.py`, `ruuvi_collector.py`, `ruuvi_store.py`) are now compatibility wrappers.

## Requirements

- Python 3.10+
- BLE-capable Bluetooth adapter
- MQTT broker (Mosquitto)

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate.fish
pip install -r requirements.txt
```

## Configuration

```bash
cp .env.example .env
```

Important values:

- `MQTT_HOST`
- `MQTT_PORT`
- `MQTT_TOPIC_PREFIX`
- `MQTT_TOPIC`
- `ALLOWED_MACS` (optional, comma-separated)
- `DB_PATH`
- `API_HOST`
- `API_PORT`

## Run services

Use separate terminals.

1. Store service (MQTT -> SQLite)

```bash
source .venv/bin/activate.fish
./scripts/run_store.sh
```

2. Collector service (BLE -> MQTT)

```bash
source .venv/bin/activate.fish
./scripts/run_collector.sh
```

3. API + dashboard

```bash
source .venv/bin/activate.fish
./scripts/run_api.sh
```

Open:

- Dashboard: `http://127.0.0.1:8000/dashboard`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

## Verify stored telemetry

```bash
sqlite3 telemetry.db "select id,sensor_id,iso_time,temperature_c,humidity_pct,battery_mv from telemetry order by id desc limit 10;"
```