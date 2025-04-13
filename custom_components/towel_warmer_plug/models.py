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
    manual_max_duration: int  # em minutos

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "TowelWarmerConfig":
        return TowelWarmerConfig(
            name=data[CONF_NAME],
            switch_entity=data[CONF_SWITCH],
            power_sensor=data[CONF_POWER],
            minimum_power=data.get(CONF_MINIMUM_POWER, DEFAULT_MINIMUM_POWER),
            start_time=data[CONF_START_TIME],
            end_time=data[CONF_END_TIME],
            manual_max_duration=data.get(CONF_MANUAL_MAX_DURATION, DEFAULT_MANUAL_MAX_DURATION),
        )

