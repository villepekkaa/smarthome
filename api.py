import os
import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "telemetry.db")

app = FastAPI(title="SmartHome API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if needed
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/health")
def health():
    try:
        conn = get_conn()
        cur = conn.execute("SELECT 1")
        _ = cur.fetchone()
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

    return {
        "count": len(rows),
        "items": [dict(r) for r in rows],
    }


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

    return {
        "count": len(rows),
        "items": [dict(r) for r in rows],
    }


@app.get("/history")
def history(
    sensor_id: str = Query(..., description="sensor_id, e.g. ruuvi_c7ebd8f6f019"),
    limit: int = Query(100, ge=1, le=5000),
):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            id,
            ts,
            iso_time,
            sensor_id,
            name,
            mac,
            rssi,
            temperature_c,
            humidity_pct,
            pressure_pa,
            battery_mv,
            tx_power_dbm,
            movement_counter,
            measurement_sequence
        FROM telemetry
        WHERE sensor_id = ?
        ORDER BY ts DESC, id DESC
        LIMIT ?
        """,
        (sensor_id, limit),
    ).fetchall()
    conn.close()

    return {
        "sensor_id": sensor_id,
        "count": len(rows),
        "items": [dict(r) for r in rows],
    }


@app.get("/stats")
def stats():
    conn = get_conn()
    total_rows = conn.execute("SELECT COUNT(*) AS c FROM telemetry").fetchone()["c"]
    sensor_count = conn.execute(
        "SELECT COUNT(DISTINCT sensor_id) AS c FROM telemetry"
    ).fetchone()["c"]

    newest = conn.execute(
        "SELECT MAX(ts) AS newest_ts FROM telemetry"
    ).fetchone()["newest_ts"]
    oldest = conn.execute(
        "SELECT MIN(ts) AS oldest_ts FROM telemetry"
    ).fetchone()["oldest_ts"]

    conn.close()

    return {
        "rows_total": total_rows,
        "sensors_total": sensor_count,
        "oldest_ts": oldest,
        "newest_ts": newest,
        "db_path": DB_PATH,
    }


@app.get("/")
def root():
    return {
        "name": "SmartHome API",
        "version": "0.1.0",
        "endpoints": [
            "/health",
            "/sensors",
            "/latest",
            "/latest?sensor_id=<id>",
            "/history?sensor_id=<id>&limit=100",
            "/stats",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
