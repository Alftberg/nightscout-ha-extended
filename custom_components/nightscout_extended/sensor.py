"""Nightscout telemetry sensors."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfMass

from .entity import NightscoutEntity

DESCRIPTIONS = (
    SensorEntityDescription(
        key="glucose",
        translation_key="glucose",
        device_class=SensorDeviceClass.BLOOD_GLUCOSE_CONCENTRATION,
        native_unit_of_measurement="mg/dL",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(key="trend", translation_key="trend"),
    SensorEntityDescription(
        key="glucose_timestamp",
        translation_key="glucose_timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="iob", translation_key="iob", native_unit_of_measurement="U",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="cob", translation_key="cob", native_unit_of_measurement=UnitOfMass.GRAMS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="reservoir", translation_key="reservoir", native_unit_of_measurement="U",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pump_battery",
        translation_key="pump_battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(key="pump_model", translation_key="pump_model"),
    SensorEntityDescription(
        key="uploader_battery",
        translation_key="uploader_battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="loop_timestamp",
        translation_key="loop_timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(NightscoutSensor(entry, description) for description in DESCRIPTIONS)


class NightscoutSensor(NightscoutEntity, SensorEntity):
    @property
    def native_value(self):
        return self.value
