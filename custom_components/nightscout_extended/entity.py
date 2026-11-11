"""Shared entity behavior."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class NightscoutEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry, description):
        super().__init__(entry.runtime_data)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Nightscout",
        )

    @property
    def value(self):
        return self.coordinator.data.get(self.entity_description.key)
