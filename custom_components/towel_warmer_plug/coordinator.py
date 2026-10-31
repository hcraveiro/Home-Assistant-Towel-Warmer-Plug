from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity_component import DEFAULT_SCAN_INTERVAL
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
import logging

from .const import *
from .models import TowelWarmerConfig
from .utils import slugify, _safe_parse_dt
from .schedule import is_in_schedule

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

    def _is_on(self, state):
        """Determine whether the configured switch or climate is enabled."""
        if self.config.switch_entity.startswith("climate."):
            return state.state not in ("off", "unknown", "unavailable")
        return state.state == "on"

    async def _set_enabled(self, enabled):
        """Control either a switch or a climate entity using its native service."""
        entity_id = self.config.switch_entity
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            raise UpdateFailed(f"Control entity {entity_id} is not available")
        if entity_id.startswith("climate."):
            modes = state.attributes.get("hvac_modes", [])
            if enabled:
                mode = next((candidate for candidate in ("heat", "auto", "on") if candidate in modes), None)
                if mode is None:
                    raise UpdateFailed(f"{entity_id} supports none of heat, auto, or on: {modes}")
            else:
                if "off" not in modes:
                    raise UpdateFailed(f"{entity_id} does not support off mode: {modes}")
                mode = "off"
            _LOGGER.info("%s - Setting %s HVAC mode to %s", self.config.name, entity_id, mode)
            await self.hass.services.async_call(
                "climate", "set_hvac_mode",
                {"entity_id": entity_id, "hvac_mode": mode},
                blocking=True,
            )
        else:
            await self.hass.services.async_call(
                "switch", "turn_on" if enabled else "turn_off",
                {"entity_id": entity_id}, blocking=True,
            )

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

            if state_switch.state in ("unknown", "unavailable"):
                raise UpdateFailed("Control entity is unavailable")
            is_on = self._is_on(state_switch)
            power = float(state_power.state)

            inside_schedule = is_in_schedule(
                dt_util.now(), self.config.weekdays, self.config.time_windows
            )

            # Detect manual override via switch state change
            previous_state = self._last_switch_state
            self._last_switch_state = state_switch.state

            if previous_state is not None and previous_state != state_switch.state:
                if is_on and not self._auto_turning_on:
                    self._manual_override = True
                    self._manual_override_since = dt_util.now()
                    _LOGGER.debug(f"{self.config.name} - Manual override detected: switch turned on manually.")
                    await self.save_persistent_data()
                elif not is_on:
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
                    await self._set_enabled(False)
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
                    await self._set_enabled(True)
                    self._last_auto_on = dt_util.now()
                    self._manual_override = False
                    self._manual_override_since = None
                    await self.save_persistent_data()
                elif not inside_schedule and is_on and not self._manual_override:
                    _LOGGER.info(f"{self.config.name} - Outside schedule. Turning off towel warmer...")
                    await self._set_enabled(False)
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
        if not data:
            _LOGGER.debug("%s - No persistent data found; starting fresh.", self.config.name)
            return

        self._last_auto_on = _safe_parse_dt(data.get("last_auto_on"))
        self._power_low_since = _safe_parse_dt(data.get("power_low_since"))
        self._manual_override = bool(data.get("manual_override", False))
        self._manual_override_since = _safe_parse_dt(data.get("manual_override_since"))
        self._last_switch_state = data.get("last_switch_state", None)

        _LOGGER.debug(
            "%s - Loaded persistent: last_auto_on=%s, power_low_since=%s, "
            "manual_override=%s, manual_override_since=%s, last_switch_state=%s",
            self.config.name,
            self._last_auto_on,
            self._power_low_since,
            self._manual_override,
            self._manual_override_since,
            self._last_switch_state,
        )

    async def save_persistent_data(self):
        try:
            await self.storage.async_save({
                "last_auto_on": self._last_auto_on.isoformat() if self._last_auto_on else None,
                "power_low_since": self._power_low_since.isoformat() if self._power_low_since else None,
                "manual_override": self._manual_override,
                "manual_override_since": self._manual_override_since.isoformat() if self._manual_override_since else None,
                "last_switch_state": self._last_switch_state,
                "is_full_latched": getattr(self, "_is_full_latched", None),  # só no dehumidifier_plug
            })
        except Exception as err:
            _LOGGER.warning("%s - Failed to save persistent data: %s", self.config.name, err)

