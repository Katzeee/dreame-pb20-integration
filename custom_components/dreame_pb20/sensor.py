"""Verified PB20 air measurements and filter life."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfDensity,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PB20ConfigEntry
from .entity import PB20Entity

SENSORS = (
    SensorEntityDescription(
        key="aq",
        translation_key="aq",
        icon="mdi:leaf",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="filter_days_remaining",
        translation_key="filter_days_remaining",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="pm25",
        device_class=SensorDeviceClass.PM25,
        native_unit_of_measurement=UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="pm10",
        device_class=SensorDeviceClass.PM10,
        native_unit_of_measurement=UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="formaldehyde",
        translation_key="formaldehyde",
        icon="mdi:molecule",
        native_unit_of_measurement=UnitOfDensity.MILLIGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="air_quality",
        translation_key="air_quality",
        device_class=SensorDeviceClass.ENUM,
        options=["excellent", "good", "average", "poor"],
    ),
    SensorEntityDescription(
        key="filter_remaining",
        translation_key="filter_remaining",
        icon="mdi:air-filter",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: PB20ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(PB20Sensor(entry.runtime_data, description) for description in SENSORS)


class PB20Sensor(PB20Entity, SensorEntity):
    """Expose unknown and standby air measurements as unavailable."""

    def __init__(self, coordinator, description: SensorEntityDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return getattr(self.coordinator.data, self.entity_description.key)

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.native_value is not None
            and (
                self.entity_description.key in ("filter_remaining", "filter_days_remaining")
                or self.coordinator.data.power is True
                or self.coordinator.data.continuous_monitoring is True
            )
        )
