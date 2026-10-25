from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from homeassistant.helpers import selector

from .const import (
    DOMAIN, CONF_NAME, CONF_SWITCH, CONF_POWER,
    CONF_START_TIME, CONF_END_TIME,
    DEFAULT_START_TIME, DEFAULT_END_TIME,
    CONF_MINIMUM_POWER, DEFAULT_MINIMUM_POWER,
    CONF_WEEKDAYS, DEFAULT_WEEKDAYS, CONF_TIME_WINDOWS,
    CONF_START_TIME_2, CONF_END_TIME_2, CONF_START_TIME_3, CONF_END_TIME_3,
)

CONF_MANUAL_MAX_DURATION = "manual_max_duration"
DEFAULT_MANUAL_MAX_DURATION = 60  # minutes

WEEKDAY_SELECTOR = selector.SelectSelector(selector.SelectSelectorConfig(
    options=[selector.SelectOptionDict(value=value, label=label) for value, label in [
        ("mon", "Monday"), ("tue", "Tuesday"), ("wed", "Wednesday"),
        ("thu", "Thursday"), ("fri", "Friday"), ("sat", "Saturday"), ("sun", "Sunday"),
    ]], multiple=True, mode=selector.SelectSelectorMode.DROPDOWN,
))


TIME_WINDOWS_SELECTOR = selector.ObjectSelector(selector.ObjectSelectorConfig(
    multiple=True,
    label_field="start",
    description_field="end",
    fields={
        "start": {"label": "Start time", "selector": selector.TimeSelector(), "required": True},
        "end": {"label": "End time", "selector": selector.TimeSelector(), "required": True},
    },
))


def schedule_fields(values):
    """Return the weekday picker and dynamic schedule editor."""
    windows = values.get(CONF_TIME_WINDOWS)
    if windows is None:
        windows = [{
            "start": values.get(CONF_START_TIME, DEFAULT_START_TIME),
            "end": values.get(CONF_END_TIME, DEFAULT_END_TIME),
        }]
    return {
        vol.Required(CONF_WEEKDAYS, default=values.get(CONF_WEEKDAYS, DEFAULT_WEEKDAYS)): WEEKDAY_SELECTOR,
        vol.Required(CONF_TIME_WINDOWS, default=windows): TIME_WINDOWS_SELECTOR,
    }


def valid_schedule(data):
    """At least one complete interval is required."""
    windows = data.get(CONF_TIME_WINDOWS, [])
    return bool(windows) and all(
        isinstance(window, dict) and bool(window.get("start")) and bool(window.get("end"))
        for window in windows
    )


class TowelWarmerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TowelWarmerOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        if user_input is not None and valid_schedule(user_input):
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            errors={"base": "invalid_schedule"} if user_input is not None else {},
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
                vol.Optional(CONF_MANUAL_MAX_DURATION, default=DEFAULT_MANUAL_MAX_DURATION): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=360, step=1, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX)
                ),
                **schedule_fields(user_input or {}),
            })
        )

class TowelWarmerOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None and valid_schedule(user_input):
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data_fallback = self.config_entry.data
        schedule_values = {**data_fallback, **options, **(user_input or {})}

        return self.async_show_form(
            step_id="init",
            errors={"base": "invalid_schedule"} if user_input is not None else {},
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_MINIMUM_POWER,
                    default=options.get(CONF_MINIMUM_POWER, data_fallback.get(CONF_MINIMUM_POWER, DEFAULT_MINIMUM_POWER))
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=500, step=0.1, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_MANUAL_MAX_DURATION,
                    default=options.get(CONF_MANUAL_MAX_DURATION, data_fallback.get(CONF_MANUAL_MAX_DURATION, DEFAULT_MANUAL_MAX_DURATION))
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=360, step=1, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX)
                ),
                **schedule_fields(schedule_values),
            })
        )
        
        
