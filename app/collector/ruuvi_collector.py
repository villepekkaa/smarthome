import asyncio
import signal
import time
from collections import defaultdict

from bleak import BleakScanner

from app.collector.mqtt_publisher import build_mqtt_client, publish_telemetry
from app.collector.ruuvi_parser import RUUVI_COMPANY_ID, parse_ruuvi_rawv2
from app.config import get_settings


def _is_mac_allowed(mac: str) -> bool:
    settings = get_settings()
    if not settings.allowed_macs:
        return True
    return mac.upper() in settings.allowed_macs


async def main():
    stop_event = asyncio.Event()
    stats_interval_s = 30
    sensor_counts: dict[str, int] = defaultdict(int)
    sensor_last_seen_ts: dict[str, int] = {}
    last_stats_print_ts = 0

    def _stop(*_):
        stop_event.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    mqtt_client = build_mqtt_client()

    def detection_callback(device, advertisement_data):
        nonlocal last_stats_print_ts

        mac = (device.address or "").upper()
        if not _is_mac_allowed(mac):
            return

        mfg = advertisement_data.manufacturer_data or {}
        if RUUVI_COMPANY_ID not in mfg:
            return

        payload = mfg[RUUVI_COMPANY_ID]
        parsed = parse_ruuvi_rawv2(payload)
        if not parsed:
            return

        ts = int(time.time())
        sensor_id = device.address.replace(":", "").lower()

        msg = {
            "sensor_id": f"ruuvi_{sensor_id}",
            "mac": device.address,
            "name": device.name,
            "ts": ts,
            "rssi": advertisement_data.rssi,
            "values": {
                "temperature_c": round(parsed.temperature_c, 3),
                "humidity_pct": round(parsed.humidity_pct, 3),
                "pressure_pa": round(parsed.pressure_pa, 1),
                "accel_x_mg": parsed.accel_x_mg,
                "accel_y_mg": parsed.accel_y_mg,
                "accel_z_mg": parsed.accel_z_mg,
                "battery_mv": parsed.battery_mv,
                "tx_power_dbm": parsed.tx_power_dbm,
                "movement_counter": parsed.movement_counter,
                "measurement_sequence": parsed.measurement_sequence,
            },
        }

        publish_telemetry(mqtt_client, msg["sensor_id"], msg)

        sensor_id_value = msg["sensor_id"]
        sensor_counts[sensor_id_value] += 1
        sensor_last_seen_ts[sensor_id_value] = ts

        if ts - last_stats_print_ts >= stats_interval_s:
            last_stats_print_ts = ts
            parts = []
            now_ts = int(time.time())
            for sid in sorted(sensor_last_seen_ts):
                age_s = now_ts - sensor_last_seen_ts[sid]
                parts.append(f"{sid}: packets={sensor_counts[sid]}, age={age_s}s")
            if parts:
                print("Collector stats | " + " | ".join(parts))

    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    print("Scanning RuuviTag BLE advertisements... Ctrl+C to stop")

    await stop_event.wait()

    await scanner.stop()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
