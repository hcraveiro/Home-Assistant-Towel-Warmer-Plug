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

            # Atualiza manual_override com tolerância de 5s
            if is_on and self._last_auto_on:
                delta = state_switch.last_changed - self._last_auto_on
                if delta.total_seconds() > 5:
                    self._manual_override = True
                    await self.save_persistent_data()

            _LOGGER.debug(
                f"{self.config.name} - Diagnostic state: is_on={is_on}, inside_schedule={inside_schedule}, "
                f"manual_override={self._manual_override}, auto_enabled={auto_enabled}, power={power:.2f}"
            )

            is_malfunction = False
            if is_on and power < self.config.minimum_power:
                if not self._power_low_since:
                    self._power_low_since = now_local
                    _LOGGER.debug(f"{self.config.name} - Power dropped below malfunction threshold. Starting timer...")
                    await self.save_persistent_data()
            else:
                if self._power_low_since:
                    _LOGGER.debug(f"{self.config.name} - Power normal. Clearing malfunction timer.")
                self._power_low_since = None
                await self.save_persistent_data()

            if self._power_low_since:
                elapsed = now_local - self._power_low_since
                if elapsed >= timedelta(seconds=60):
                    is_malfunction = True
                    _LOGGER.debug(f"{self.config.name} - Low power for {elapsed}. Marking as malfunction.")
                else:
                    _LOGGER.debug(f"{self.config.name} - Power low for {elapsed.total_seconds():.0f}s but not long enough.")

            # Automatic control logic
            if auto_enabled:
                if inside_schedule and not is_on:
                    _LOGGER.info(f"{self.config.name} - Inside schedule. Turning on towel warmer...")
                    await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.config.switch_entity}, blocking=True)
                    self._last_auto_on = now_local
                    self._manual_override = False  # reset se foi ação automática
                    await self.save_persistent_data()
                elif not inside_schedule and is_on and not self._manual_override:
                    _LOGGER.info(f"{self.config.name} - Outside schedule. Turning off towel warmer...")
                    await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.config.switch_entity}, blocking=True)
                    self._manual_override = False
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
            if "last_auto_on" in data and isinstance(data["last_auto_on"], str):
                self._last_auto_on = datetime.fromisoformat(data["last_auto_on"])
            if "power_low_since" in data and isinstance(data["power_low_since"], str):
                self._power_low_since = datetime.fromisoformat(data["power_low_since"])
            if "manual_override" in data:
                self._manual_override = data["manual_override"]

    async def save_persistent_data(self):
        await self.storage.async_save({
            "last_auto_on": self._last_auto_on.isoformat() if self._last_auto_on else None,
            "power_low_since": self._power_low_since.isoformat() if self._power_low_since else None,
            "manual_override": self._manual_override,
        })
