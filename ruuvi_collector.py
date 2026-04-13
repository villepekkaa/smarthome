import asyncio
import json
import os
import signal
import time
from dataclasses import dataclass
from typing import Optional

from bleak import BleakScanner
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "home/ruuvi")

# Comma-separated MAC list in .env
# Example: ALLOWED_MACS=EA:10:CF:D3:59:AD,C7:EB:D8:F6:F0:19
_allowed_macs_raw = os.getenv("ALLOWED_MACS", "")
ALLOWED_MACS = {
    mac.strip().upper()
    for mac in _allowed_macs_raw.split(",")
    if mac.strip()
}

# Ruuvi manufacturer ID (little-endian bytes in BLE payload often appear as 0x0499)
RUUVI_COMPANY_ID = 0x0499


@dataclass
class RuuviData:
    temperature_c: float
    humidity_pct: float
    pressure_pa: float
    accel_x_mg: int
    accel_y_mg: int
    accel_z_mg: int
    battery_mv: int
    tx_power_dbm: int
    movement_counter: int
    measurement_sequence: int


def twos_complement(value: int, bits: int) -> int:
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return value


def parse_ruuvi_rawv2(payload: bytes) -> Optional[RuuviData]:
    """
    Parse Ruuvi Data Format 5 (RAWv2), 24 bytes:
    Byte 0: format (0x05)
    1-2 temp, 3-4 humidity, 5-6 pressure, 7-12 accel xyz,
    13-14 power info, 15 movement, 16-17 sequence, 18-23 MAC (optional in adv)
    """
    if len(payload) < 18:
        return None

    if payload[0] != 0x05:
        return None

    temp_raw = twos_complement((payload[1] << 8) | payload[2], 16)
    hum_raw = (payload[3] << 8) | payload[4]
    pres_raw = (payload[5] << 8) | payload[6]

    ax = twos_complement((payload[7] << 8) | payload[8], 16)
    ay = twos_complement((payload[9] << 8) | payload[10], 16)
    az = twos_complement((payload[11] << 8) | payload[12], 16)

    power_raw = (payload[13] << 8) | payload[14]
    movement = payload[15]
    seq = (payload[16] << 8) | payload[17]

    temperature_c = temp_raw * 0.005
    humidity_pct = hum_raw * 0.0025
    pressure_pa = pres_raw + 50000

    battery_mv = (power_raw >> 5) + 1600
    tx_power_dbm = (power_raw & 0x1F) * 2 - 40

    return RuuviData(
        temperature_c=temperature_c,
        humidity_pct=humidity_pct,
        pressure_pa=pressure_pa,
        accel_x_mg=ax,
        accel_y_mg=ay,
        accel_z_mg=az,
        battery_mv=battery_mv,
        tx_power_dbm=tx_power_dbm,
        movement_counter=movement,
        measurement_sequence=seq,
    )


def build_mqtt_client() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    return client


async def main():
    stop_event = asyncio.Event()

    def _stop(*_):
        stop_event.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    mqtt_client = build_mqtt_client()

    def detection_callback(device, advertisement_data):
        mac = (device.address or "").upper()
        
        # If allowlist is provided, enforce it. If empty, allow all.
        if ALLOWED_MACS and mac not in ALLOWED_MACS:
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

        topic = f"{MQTT_TOPIC_PREFIX}/{msg['sensor_id']}/telemetry"
        mqtt_client.publish(topic, json.dumps(msg), qos=0, retain=False)
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
