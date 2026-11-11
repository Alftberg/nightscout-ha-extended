"""Report the last Loop result."""

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription

from .entity import NightscoutEntity

DESCRIPTION = BinarySensorEntityDescription(key="loop_ok", translation_key="loop_ok")


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([LoopStatus(entry, DESCRIPTION)])


class LoopStatus(NightscoutEntity, BinarySensorEntity):
    @property
    def is_on(self):
        return self.value
