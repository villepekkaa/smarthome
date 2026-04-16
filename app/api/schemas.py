from typing import Optional

from pydantic import BaseModel


class SensorTelemetry(BaseModel):
    id: Optional[int] = None
    ts: Optional[int] = None
    iso_time: Optional[str] = None
    sensor_id: str
    name: Optional[str] = None
    mac: Optional[str] = None
    rssi: Optional[int] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_pa: Optional[float] = None
    battery_mv: Optional[int] = None
    tx_power_dbm: Optional[int] = None
    movement_counter: Optional[int] = None
    measurement_sequence: Optional[int] = None


class SensorListResponse(BaseModel):
    count: int
    items: list[SensorTelemetry]


class HistoryResponse(BaseModel):
    sensor_id: str
    count: int
    items: list[SensorTelemetry]


class AlertValues(BaseModel):
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_pa: Optional[float] = None
    battery_mv: Optional[int] = None
    movement_counter: Optional[int] = None
    measurement_sequence: Optional[int] = None


class AlertItem(BaseModel):
    sensor_id: str
    name: Optional[str] = None
    mac: Optional[str] = None
    ts: Optional[int] = None
    iso_time: Optional[str] = None
    rssi: Optional[int] = None
    severity: str
    type: str
    message: str
    values: AlertValues


class AlertListResponse(BaseModel):
    count: int
    items: list[AlertItem]


class AlertSummaryResponse(BaseModel):
    count_total: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
