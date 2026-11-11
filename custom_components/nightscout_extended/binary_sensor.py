"""Report Loop and pump status."""

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription

from .entity import NightscoutEntity

DESCRIPTIONS = tuple(
    BinarySensorEntityDescription(key=key, translation_key=key)
    for key in ("loop_ok", "pump_suspended", "pump_bolusing")
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(NightscoutBinarySensor(entry, description) for description in DESCRIPTIONS)


class NightscoutBinarySensor(NightscoutEntity, BinarySensorEntity):
    @property
    def is_on(self):
        return self.value
