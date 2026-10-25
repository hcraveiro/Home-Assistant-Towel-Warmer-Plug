from dataclasses import dataclass
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
)

CONF_MANUAL_MAX_DURATION = "manual_max_duration"
DEFAULT_MANUAL_MAX_DURATION = 60  # minutes

def merge_entry_settings(data: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    """Preserve original settings when legacy options contain null values."""
    return {**data, **{key: value for key, value in options.items() if value is not None}}


@dataclass
class TowelWarmerConfig:
    name: str
    switch_entity: str
    power_sensor: str
    minimum_power: float
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
            manual_max_duration=data.get(CONF_MANUAL_MAX_DURATION, DEFAULT_MANUAL_MAX_DURATION),
            weekdays=data.get(CONF_WEEKDAYS, DEFAULT_WEEKDAYS),
            time_windows=[
                (window["start"], window["end"])
                for window in data[CONF_TIME_WINDOWS]
            ] if CONF_TIME_WINDOWS in data else [
                (data.get(CONF_START_TIME, "09:00:00"), data.get(CONF_END_TIME, "20:00:00"))
            ],
        )

