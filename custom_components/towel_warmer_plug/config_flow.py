from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from homeassistant.helpers import selector

from .const import (
    DOMAIN, CONF_NAME, CONF_SWITCH, CONF_POWER,
    CONF_START_TIME, CONF_END_TIME,
    DEFAULT_START_TIME, DEFAULT_END_TIME,
    CONF_MINIMUM_POWER, DEFAULT_MINIMUM_POWER,
)

CONF_MANUAL_MAX_DURATION = "manual_max_duration"
DEFAULT_MANUAL_MAX_DURATION = 60  # minutos

class TowelWarmerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TowelWarmerOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): selector.TextSelector(),
                vol.Required(CONF_SWITCH): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Required(CONF_POWER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_MINIMUM_POWER, default=DEFAULT_MINIMUM_POWER): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=500, step=0.1, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_START_TIME, default=DEFAULT_START_TIME): selector.TimeSelector(),
                vol.Optional(CONF_END_TIME, default=DEFAULT_END_TIME): selector.TimeSelector(),
                vol.Optional(CONF_MANUAL_MAX_DURATION, default=DEFAULT_MANUAL_MAX_DURATION): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=360, step=1, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX)
                ),
            })
        )

class TowelWarmerOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data_fallback = self.config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_MINIMUM_POWER,
                    default=options.get(CONF_MINIMUM_POWER, data_fallback.get(CONF_MINIMUM_POWER, DEFAULT_MINIMUM_POWER))
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=500, step=0.1, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_START_TIME,
                    default=options.get(CONF_START_TIME, data_fallback.get(CONF_START_TIME, DEFAULT_START_TIME))
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_END_TIME,
                    default=options.get(CONF_END_TIME, data_fallback.get(CONF_END_TIME, DEFAULT_END_TIME))
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_MANUAL_MAX_DURATION,
                    default=options.get(CONF_MANUAL_MAX_DURATION, data_fallback.get(CONF_MANUAL_MAX_DURATION, DEFAULT_MANUAL_MAX_DURATION))
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=360, step=1, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX)
                ),
            })
        )
        
        
