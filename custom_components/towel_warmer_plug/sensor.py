from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from .const import DOMAIN
from .utils import slugify

SENSOR_TYPES: dict[str, SensorEntityDescription] = {
    "status": SensorEntityDescription(
        key="status",
        name="Status",
        icon="mdi:radiator",
    ),
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entity_registry = async_get_entity_registry(hass)
    device_registry = async_get_device_registry(hass)
    entity_entry = entity_registry.async_get(coordinator.config.switch_entity)
    device_entry = device_registry.async_get(entity_entry.device_id) if entity_entry else None
    device_identifiers = device_entry.identifiers if device_entry else None

    entities = [
        TowelWarmerSensor(coordinator, sensor_id, description, device_identifiers)
        for sensor_id, description in SENSOR_TYPES.items()
    ]
    async_add_entities(entities)

class TowelWarmerSensor(SensorEntity):
    def __init__(self, coordinator, sensor_id, description, device_identifiers):
        self.coordinator = coordinator
        self.sensor_id = sensor_id
        self.entity_description = description
        object_id = slugify(f"{coordinator.config.name}_{sensor_id}")
        self._attr_name = f"{coordinator.config.name} {description.name}"
        self._attr_unique_id = f"towel_warmer_{object_id}"
        if sensor_id != "status":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._device_identifiers = device_identifiers

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None
    
        if data.get("is_malfunction"):
            return "Malfunction"
        if data.get("manual_override"):
            return "Warming"
        if data.get("is_on"):
            return "Warming"
        if not data.get("inside_schedule"):
            return "Outside warming hours"
        return "Idle"

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        if self._device_identifiers:
            return {"identifiers": self._device_identifiers}
        return None

    async def async_update(self):
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        ) 

