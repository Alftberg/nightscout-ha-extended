"""Nightscout telemetry sensors."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT, PERCENTAGE, UnitOfMass, UnitOfTime

from .const import AGE_EVENTS, GLUCOSE_SENSOR_KEYS, TREND_STATES
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
        key="trend_text",
        translation_key="trend_text",
        device_class=SensorDeviceClass.ENUM,
        options=list(TREND_STATES.values()),
    ),
    SensorEntityDescription(
        key="glucose_delta",
        translation_key="glucose_delta",
        device_class=SensorDeviceClass.BLOOD_GLUCOSE_CONCENTRATION,
        native_unit_of_measurement="mg/dL",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="glucose_timestamp",
        translation_key="glucose_timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="iob", translation_key="iob", native_unit_of_measurement="U",
        suggested_display_precision=2,
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
    *(
        SensorEntityDescription(
            key=key,
            translation_key=key,
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.HOURS,
            suggested_display_precision=1,
        )
        for key in AGE_EVENTS
    ),
    SensorEntityDescription(key="override_profile", translation_key="override_profile"),
    SensorEntityDescription(key="loop_version", translation_key="loop_version"),
    SensorEntityDescription(
        key="pump_timestamp",
        translation_key="pump_timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="glucose_forecast",
        translation_key="glucose_forecast",
        device_class=SensorDeviceClass.BLOOD_GLUCOSE_CONCENTRATION,
        native_unit_of_measurement="mg/dL",
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
    def __init__(self, entry, description):
        super().__init__(entry, description)
        if description.key in GLUCOSE_SENSOR_KEYS:
            self._attr_suggested_unit_of_measurement = entry.options.get(
                CONF_UNIT_OF_MEASUREMENT
            )

    @property
    def native_value(self):
        if self.entity_description.key == "trend_text":
            return TREND_STATES.get(self.coordinator.data.get("trend"))
        return self.value

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "override_profile" and self.available:
            return self.coordinator.data.get("override_attributes")
        if self.entity_description.key == "glucose_forecast" and self.value is not None:
            return {"forecast_points": self.coordinator.data["forecast_points"]}
        return None
