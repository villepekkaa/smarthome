import asyncio
import signal
import time

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

    def _stop(*_):
        stop_event.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    mqtt_client = build_mqtt_client()

    def detection_callback(device, advertisement_data):
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

        topic = publish_telemetry(mqtt_client, msg["sensor_id"], msg)
        print(topic, msg)

    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    print("Scanning RuuviTag BLE advertisements... Ctrl+C to stop")

    await stop_event.wait()

    await scanner.stop()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
