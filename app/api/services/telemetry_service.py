from app.api.db import get_conn


def fetch_sensors() -> list[dict]:
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
    return [dict(r) for r in rows]


def fetch_latest(sensor_id: str | None = None) -> list[dict]:
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
        return [dict(row)] if row else []

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
    return [dict(r) for r in rows]


def fetch_history(sensor_id: str, limit: int) -> list[dict]:
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
    return [dict(r) for r in rows]
