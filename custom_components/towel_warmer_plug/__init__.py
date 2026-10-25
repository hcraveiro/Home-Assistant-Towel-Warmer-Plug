from homeassistant.config_entries import ConfigEntry, ConfigEntryError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform

from .const import (
    DOMAIN,
    CONF_SWITCH, CONF_POWER,
    CONF_START_TIME, CONF_END_TIME,
    CONF_NAME
)
from .coordinator import TowelWarmerCoordinator
from .models import TowelWarmerConfig, merge_entry_settings

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Register the options listener before validation or the first refresh.
    # A failed setup must still recover when the user fixes the options.
    entry.async_on_unload(entry.add_update_listener(update_listener))
    # Legacy options may contain null entity references. Do not overwrite
    # valid setup values with null when loading an existing entry.
    data = {**merge_entry_settings(entry.data, entry.options), CONF_NAME: entry.title}

    if not data.get(CONF_POWER):
        raise ConfigEntryError(
            "Power sensor is not configured. Open Configure and select a Power Sensor."
        )

    config = TowelWarmerConfig.from_dict(data)
    coordinator = TowelWarmerCoordinator(hass, config)
    await coordinator.async_config_entry_first_refresh()

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Força o reload da config entry quando as opções são atualizadas."""
    await hass.config_entries.async_reload(entry.entry_id)
