import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    db_path: str = "telemetry.db"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic_prefix: str = "home/ruuvi"
    mqtt_topic: str = "home/ruuvi/+/telemetry"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    allowed_macs: set[str] = set()
    api_allowed_origins: list[str] = ["http://127.0.0.1:8000"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()

    allowed_raw = os.getenv("ALLOWED_MACS", "")
    allowed_macs = {
        mac.strip().upper()
        for mac in allowed_raw.split(",")
        if mac.strip()
    }

    return Settings(
        db_path=os.getenv("DB_PATH", "telemetry.db"),
        mqtt_host=os.getenv("MQTT_HOST", "localhost"),
        mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
        mqtt_topic_prefix=os.getenv("MQTT_TOPIC_PREFIX", "home/ruuvi"),
        mqtt_topic=os.getenv("MQTT_TOPIC", "home/ruuvi/+/telemetry"),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8000")),
        allowed_macs=allowed_macs,
        api_allowed_origins=[
            origin.strip()
            for origin in os.getenv("API_ALLOWED_ORIGINS", "http://127.0.0.1:8000").split(",")
            if origin.strip()
        ],
    )


def resolve_db_path() -> Path:
    return Path(get_settings().db_path)
