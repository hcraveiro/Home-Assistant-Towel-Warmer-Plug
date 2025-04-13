from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity_component import DEFAULT_SCAN_INTERVAL
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
import logging

from .const import *
from .models import TowelWarmerConfig
from .utils import slugify

_LOGGER = logging.getLogger(__name__)

class TowelWarmerCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: TowelWarmerConfig):
        self.hass = hass
        self.config = config
        self.storage = Store(hass, 1, f"{DOMAIN}_{slugify(config.name)}")
        self._last_auto_on = None
        self._power_low_since = None
        self._manual_override = False
        self._manual_override_since = None
        self._last_switch_state = None
        self._auto_turning_on = False

        super().__init__(
            hass,
            _LOGGER,
            name=f"TowelWarmerCoordinator_{config.name}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

        hass.loop.create_task(self.load_persistent_data())

    async def _async_update_data(self):
        try:
            state_switch = self.hass.states.get(self.config.switch_entity)
            state_power = self.hass.states.get(self.config.power_sensor)

            if not state_switch or not state_power:
                raise UpdateFailed("Missing switch or power sensor state")

            if state_power.state in ("unavailable", "unknown"):
                raise UpdateFailed("Power sensor is unavailable")

            auto_switch_id = f"switch.{slugify(f'{self.config.name}_control')}"
            state_auto = self.hass.states.get(auto_switch_id)
            auto_enabled = state_auto and state_auto.state == "on"
            _LOGGER.debug(f"{self.config.name} - Found auto switch entity: {auto_switch_id} with state: {state_auto.state if state_auto else 'Not found'}")

            is_on = state_switch.state == "on"
            power = float(state_power.state)

            now_local = dt_util.now()
            now = now_local.time()

            if isinstance(self.config.start_time, str):
                start = datetime.strptime(self.config.start_time, "%H:%M:%S").time()
            else:
                start = self.config.start_time

            if isinstance(self.config.end_time, str):
                end = datetime.strptime(self.config.end_time, "%H:%M:%S").time()
            else:
                end = self.config.end_time

            inside_schedule = start <= now <= end if start < end else now >= start or now <= end

            # Detect manual override via switch state change
            previous_state = self._last_switch_state
            self._last_switch_state = state_switch.state

            if previous_state is not None and previous_state != state_switch.state:
                if state_switch.state == "on" and not self._auto_turning_on:
                    self._manual_override = True
                    self._manual_override_since = dt_util.now()
                    _LOGGER.debug(f"{self.config.name} - Manual override detected: switch turned on manually.")
                    await self.save_persistent_data()
                elif state_switch.state == "off":
                    self._manual_override = False
                    self._manual_override_since = None
                    _LOGGER.debug(f"{self.config.name} - Switch turned off. Clearing manual override.")
                    await self.save_persistent_data()

            # Cancel auto flag
            self._auto_turning_on = False

            # Desativa manual_override após limite
            if self._manual_override and self._manual_override_since:
                elapsed = dt_util.now() - self._manual_override_since
                if elapsed.total_seconds() > self.config.manual_max_duration * 60:
                    _LOGGER.info(f"{self.config.name} - Manual override exceeded {self.config.manual_max_duration} minutes. Turning off.")
                    await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.config.switch_entity}, blocking=True)
                    self._manual_override = False
                    self._manual_override_since = None
                    await self.save_persistent_data()
                    is_on = False

            _LOGGER.debug(
                f"{self.config.name} - Diagnostic state: is_on={is_on}, inside_schedule={inside_schedule}, "
                f"manual_override={self._manual_override}, auto_enabled={auto_enabled}, power={power:.2f}"
            )

            is_malfunction = False
            if is_on and power < self.config.minimum_power:
                if not self._power_low_since:
                    self._power_low_since = dt_util.now()
                    _LOGGER.debug(f"{self.config.name} - Power dropped below malfunction threshold. Starting timer...")
                    await self.save_persistent_data()
            else:
                if self._power_low_since:
                    _LOGGER.debug(f"{self.config.name} - Power normal. Clearing malfunction timer.")
                self._power_low_since = None
                await self.save_persistent_data()

            if self._power_low_since:
                elapsed = dt_util.now() - self._power_low_since
                if elapsed >= timedelta(seconds=60):
                    is_malfunction = True
                    _LOGGER.debug(f"{self.config.name} - Low power for {elapsed}. Marking as malfunction.")
                else:
                    _LOGGER.debug(f"{self.config.name} - Power low for {elapsed.total_seconds():.0f}s but not long enough.")

            # Automatic control logic
            if auto_enabled:
                if inside_schedule and not is_on:
                    _LOGGER.info(f"{self.config.name} - Inside schedule. Turning on towel warmer...")
                    self._auto_turning_on = True
                    await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.config.switch_entity}, blocking=True)
                    self._last_auto_on = dt_util.now()
                    self._manual_override = False
                    self._manual_override_since = None
                    await self.save_persistent_data()
                elif not inside_schedule and is_on and not self._manual_override:
                    _LOGGER.info(f"{self.config.name} - Outside schedule. Turning off towel warmer...")
                    await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.config.switch_entity}, blocking=True)
                    self._manual_override = False
                    self._manual_override_since = None
                    await self.save_persistent_data()

            return {
                "is_on": is_on,
                "power": power,
                "inside_schedule": inside_schedule,
                "manual_override": self._manual_override,
                "is_malfunction": is_malfunction,
            }

        except Exception as e:
            raise UpdateFailed(f"Error updating towel_warmer data: {e}")

    async def load_persistent_data(self):
        data = await self.storage.async_load()
        if data:
            if "last_auto_on" in data:
                self._last_auto_on = datetime.fromisoformat(data["last_auto_on"])
            if "power_low_since" in data:
                self._power_low_since = datetime.fromisoformat(data["power_low_since"])
            self._manual_override = data.get("manual_override", False)
            since = data.get("manual_override_since")
            if since:
                self._manual_override_since = datetime.fromisoformat(since)
            self._last_switch_state = data.get("last_switch_state", None)

    async def save_persistent_data(self):
        await self.storage.async_save({
            "last_auto_on": self._last_auto_on.isoformat() if self._last_auto_on else None,
            "power_low_since": self._power_low_since.isoformat() if self._power_low_since else None,
            "manual_override": self._manual_override,
            "manual_override_since": self._manual_override_since.isoformat() if self._manual_override_since else None,
            "last_switch_state": self._last_switch_state,
        })

