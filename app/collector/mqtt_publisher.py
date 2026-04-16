import json

import paho.mqtt.client as mqtt

from app.config import get_settings


def build_mqtt_client() -> mqtt.Client:
    settings = get_settings()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
    client.loop_start()
    return client


def publish_telemetry(client: mqtt.Client, sensor_id: str, msg: dict) -> str:
    topic = f"{get_settings().mqtt_topic_prefix}/{sensor_id}/telemetry"
    client.publish(topic, json.dumps(msg), qos=0, retain=False)
    return topic
