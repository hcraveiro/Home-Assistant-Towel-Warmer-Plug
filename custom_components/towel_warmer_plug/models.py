from dataclasses import dataclass
from datetime import time
from typing import Any

from .const import (
    CONF_NAME,
    CONF_SWITCH,
    CONF_POWER,
    CONF_START_TIME,
    CONF_END_TIME,
    CONF_MINIMUM_POWER,
    DEFAULT_MINIMUM_POWER,
    CONF_WEEKDAYS, DEFAULT_WEEKDAYS, CONF_TIME_WINDOWS,
    CONF_START_TIME_2, CONF_END_TIME_2, CONF_START_TIME_3, CONF_END_TIME_3,
)

CONF_MANUAL_MAX_DURATION = "manual_max_duration"
DEFAULT_MANUAL_MAX_DURATION = 60  # minutos

@dataclass
class TowelWarmerConfig:
    name: str
    switch_entity: str
    power_sensor: str
    minimum_power: float
    start_time: time
    end_time: time
    manual_max_duration: int  # minutes
    weekdays: list[str]
    time_windows: list[tuple[str, str]]

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "TowelWarmerConfig":
        return TowelWarmerConfig(
            name=data[CONF_NAME],
            switch_entity=data[CONF_SWITCH],
            power_sensor=data[CONF_POWER],
            minimum_power=data.get(CONF_MINIMUM_POWER, DEFAULT_MINIMUM_POWER),
            start_time=data.get(CONF_START_TIME, data.get(CONF_TIME_WINDOWS, [{"start": "09:00:00"}])[0]["start"]),
            end_time=data.get(CONF_END_TIME, data.get(CONF_TIME_WINDOWS, [{"end": "20:00:00"}])[0]["end"]),
            manual_max_duration=data.get(CONF_MANUAL_MAX_DURATION, DEFAULT_MANUAL_MAX_DURATION),
            weekdays=data.get(CONF_WEEKDAYS, DEFAULT_WEEKDAYS),
            time_windows=[
                (window["start"], window["end"])
                for window in data[CONF_TIME_WINDOWS]
            ] if CONF_TIME_WINDOWS in data else [
                (data[CONF_START_TIME], data[CONF_END_TIME])
            ],

        )

