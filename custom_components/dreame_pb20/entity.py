"""Shared device identity for PB20 entities."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PB20Coordinator


class PB20Entity(CoordinatorEntity[PB20Coordinator]):
    """Attach each entity to the selected PB20 device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PB20Coordinator, key: str) -> None:
        super().__init__(coordinator)
        info = coordinator.device.info
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.unique_id)},
            manufacturer="Dreame",
            model="Air Purifier PB20",
            model_id="dreame.airp.u2605",
            name=info.name,
            sw_version=info.firmware,
        )
