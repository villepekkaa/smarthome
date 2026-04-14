import os
import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "telemetry.db")

app = FastAPI(title="SmartHome API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _compute_alerts_from_latest(
    offline_min: int,
    battery_low_mv: int,
    humidity_warn_pct: float,
    temp_high_c: float,
):
    conn = get_conn()

    latest_rows = conn.execute(
        """
        SELECT t.*
        FROM telemetry t
        JOIN (
            SELECT sensor_id, MAX(ts) AS max_ts
            FROM telemetry
            GROUP BY sensor_id
        ) x
          ON t.sensor_id = x.sensor_id
         AND t.ts = x.max_ts
        ORDER BY t.sensor_id
        """
    ).fetchall()

    now_row = conn.execute("SELECT CAST(strftime('%s','now') AS INTEGER) AS now_ts").fetchone()
    now_ts = int(now_row["now_ts"])
    conn.close()

    alerts = []
    for row in latest_rows:
        r = dict(row)
        sensor_id = r["sensor_id"]
        ts = r["ts"] or 0
        age_min = (now_ts - ts) / 60 if ts else 999999

        reasons = []

        if age_min > offline_min:
            reasons.append(
                {
                    "type": "offline",
                    "severity": "danger",
                    "message": f"Sensor offline ({age_min:.1f} min since last sample)",
                }
            )

        battery_mv = r.get("battery_mv")
        if battery_mv is not None and battery_mv < battery_low_mv:
            reasons.append(
                {
                    "type": "battery_low",
                    "severity": "warn",
                    "message": f"Battery low ({battery_mv} mV < {battery_low_mv} mV)",
                }
            )

        humidity_pct = r.get("humidity_pct")
        if humidity_pct is not None and humidity_pct >= humidity_warn_pct:
            reasons.append(
                {
                    "type": "humidity_high",
                    "severity": "warn",
                    "message": f"Humidity high ({humidity_pct:.2f}% >= {humidity_warn_pct}%)",
                }
            )

        temperature_c = r.get("temperature_c")
        if temperature_c is not None and temperature_c >= temp_high_c:
            reasons.append(
                {
                    "type": "temperature_high",
                    "severity": "warn",
                    "message": f"Temperature high ({temperature_c:.2f}°C >= {temp_high_c}°C)",
                }
            )

        for reason in reasons:
            alerts.append(
                {
                    "sensor_id": sensor_id,
                    "name": r.get("name"),
                    "mac": r.get("mac"),
                    "ts": ts,
                    "iso_time": r.get("iso_time"),
                    "rssi": r.get("rssi"),
                    "severity": reason["severity"],
                    "type": reason["type"],
                    "message": reason["message"],
                    "values": {
                        "temperature_c": r.get("temperature_c"),
                        "humidity_pct": r.get("humidity_pct"),
                        "pressure_pa": r.get("pressure_pa"),
                        "battery_mv": r.get("battery_mv"),
                        "movement_counter": r.get("movement_counter"),
                        "measurement_sequence": r.get("measurement_sequence"),
                    },
                }
            )

    # danger first, then warn
    sev_rank = {"danger": 0, "warn": 1}
    alerts.sort(key=lambda a: (sev_rank.get(a["severity"], 99), a["sensor_id"]))
    return alerts


@app.get("/health")
def health():
    try:
        conn = get_conn()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return {"status": "ok", "db_path": DB_PATH}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"health check failed: {e}")


@app.get("/sensors")
def sensors():
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            sensor_id,
            MAX(name) AS name,
            MAX(mac) AS mac,
            COUNT(*) AS samples,
            MAX(ts) AS last_ts
        FROM telemetry
        GROUP BY sensor_id
        ORDER BY sensor_id
        """
    ).fetchall()
    conn.close()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


@app.get("/latest")
def latest(sensor_id: Optional[str] = None):
    conn = get_conn()

    if sensor_id:
        row = conn.execute(
            """
            SELECT *
            FROM telemetry
            WHERE sensor_id = ?
            ORDER BY ts DESC, id DESC
            LIMIT 1
            """,
            (sensor_id,),
        ).fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"sensor not found: {sensor_id}")
        return dict(row)

    rows = conn.execute(
        """
        SELECT t.*
        FROM telemetry t
        JOIN (
            SELECT sensor_id, MAX(ts) AS max_ts
            FROM telemetry
            GROUP BY sensor_id
        ) x
          ON t.sensor_id = x.sensor_id
         AND t.ts = x.max_ts
        ORDER BY t.sensor_id
        """
    ).fetchall()
    conn.close()

    return {"count": len(rows), "items": [dict(r) for r in rows]}


@app.get("/history")
def history(
    sensor_id: str = Query(..., description="sensor_id, e.g. ruuvi_c7ebd8f6f019"),
    limit: int = Query(100, ge=1, le=5000),
):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            id, ts, iso_time, sensor_id, name, mac, rssi,
            temperature_c, humidity_pct, pressure_pa, battery_mv,
            tx_power_dbm, movement_counter, measurement_sequence
        FROM telemetry
        WHERE sensor_id = ?
        ORDER BY ts DESC, id DESC
        LIMIT ?
        """,
        (sensor_id, limit),
    ).fetchall()
    conn.close()

    return {"sensor_id": sensor_id, "count": len(rows), "items": [dict(r) for r in rows]}


@app.get("/alerts")
def alerts(
    offline_min: int = Query(15, ge=1, le=1440),
    battery_low_mv: int = Query(2600, ge=1500, le=4000),
    humidity_warn_pct: float = Query(70.0, ge=0, le=100),
    temp_high_c: float = Query(28.0, ge=-50, le=120),
):
    items = _compute_alerts_from_latest(
        offline_min=offline_min,
        battery_low_mv=battery_low_mv,
        humidity_warn_pct=humidity_warn_pct,
        temp_high_c=temp_high_c,
    )
    return {"count": len(items), "items": items}


@app.get("/alert-summary")
def alert_summary(
    offline_min: int = Query(15, ge=1, le=1440),
    battery_low_mv: int = Query(2600, ge=1500, le=4000),
    humidity_warn_pct: float = Query(70.0, ge=0, le=100),
    temp_high_c: float = Query(28.0, ge=-50, le=120),
):
    items = _compute_alerts_from_latest(
        offline_min=offline_min,
        battery_low_mv=battery_low_mv,
        humidity_warn_pct=humidity_warn_pct,
        temp_high_c=temp_high_c,
    )

    by_severity = {"danger": 0, "warn": 0}
    by_type = {}
    for a in items:
        sev = a["severity"]
        typ = a["type"]
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_type[typ] = by_type.get(typ, 0) + 1

    return {
        "count_total": len(items),
        "by_severity": by_severity,
        "by_type": by_type,
    }


@app.get("/")
def root():
    return {
        "name": "SmartHome API",
        "version": "0.2.0",
        "endpoints": [
            "/health",
            "/sensors",
            "/latest",
            "/history?sensor_id=<id>&limit=100",
            "/alerts",
            "/alert-summary",
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
