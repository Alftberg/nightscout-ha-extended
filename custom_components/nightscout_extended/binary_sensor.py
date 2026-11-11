"""Report Loop and pump status."""

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription

from .entity import NightscoutEntity

DESCRIPTIONS = tuple(
    BinarySensorEntityDescription(key=key, translation_key=key)
    for key in ("loop_ok", "pump_suspended", "pump_bolusing", "uploader_charging", "override_active")
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(NightscoutBinarySensor(entry, description) for description in DESCRIPTIONS)


class NightscoutBinarySensor(NightscoutEntity, BinarySensorEntity):
    @property
    def is_on(self):
        return self.value

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "pump_suspended" and self.is_on:
            since = self.coordinator.data.get("pump_suspended_since")
            if since is not None:
                return {"first_reported_suspended_at": since.isoformat()}
        return None
