from dataclasses import dataclass
from typing import Optional


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
