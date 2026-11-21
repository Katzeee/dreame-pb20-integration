"""Explicit maintenance actions for the PB20."""

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PB20ConfigEntry, PB20Coordinator
from .entity import PB20Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: PB20ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([PB20FilterReset(entry.runtime_data)])


class PB20FilterReset(PB20Entity, ButtonEntity):
    """Enable this entity when replacing the physical filter."""

    _attr_translation_key = "reset_filter"
    _attr_icon = "mdi:filter-check"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: PB20Coordinator) -> None:
        super().__init__(coordinator, "reset_filter")

    async def async_press(self) -> None:
        await self.coordinator.command(self.coordinator.device.reset_filter)
