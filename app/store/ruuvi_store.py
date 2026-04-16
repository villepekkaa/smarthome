import json

import paho.mqtt.client as mqtt

from app.config import get_settings
from app.store.repository import init_db, insert_telemetry

settings = get_settings()
conn = init_db(settings.db_path)


def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected, subscribing:", settings.mqtt_topic)
    client.subscribe(settings.mqtt_topic)


def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode("utf-8"))
    insert_telemetry(conn, msg.topic, payload)

    values = payload.get("values", {})
    print(
        "Stored:",
        payload.get("sensor_id"),
        payload.get("ts"),
        values.get("temperature_c"),
    )


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(settings.mqtt_host, settings.mqtt_port, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
