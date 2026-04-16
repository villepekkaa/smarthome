from app.api.db import get_conn


def _fetch_latest_rows() -> tuple[list[dict], int]:
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

    now_row = conn.execute(
        "SELECT CAST(strftime('%s','now') AS INTEGER) AS now_ts"
    ).fetchone()
    conn.close()

    now_ts = int(now_row["now_ts"]) if now_row else 0
    return [dict(r) for r in latest_rows], now_ts


def compute_alerts(
    offline_min: int,
    battery_low_mv: int,
    humidity_warn_pct: float,
    temp_high_c: float,
) -> list[dict]:
    latest_rows, now_ts = _fetch_latest_rows()

    alerts: list[dict] = []

    for r in latest_rows:
        sensor_id = r["sensor_id"]
        ts = r.get("ts") or 0
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

    sev_rank = {"danger": 0, "warn": 1}
    alerts.sort(key=lambda a: (sev_rank.get(a["severity"], 99), a["sensor_id"]))
    return alerts


def summarize_alerts(alerts: list[dict]) -> dict:
    by_severity = {"danger": 0, "warn": 0}
    by_type: dict[str, int] = {}

    for alert in alerts:
        sev = alert["severity"]
        typ = alert["type"]
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_type[typ] = by_type.get(typ, 0) + 1

    return {
        "count_total": len(alerts),
        "by_severity": by_severity,
        "by_type": by_type,
    }
