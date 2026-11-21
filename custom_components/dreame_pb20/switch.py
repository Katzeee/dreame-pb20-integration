"""PB20 hardware settings."""

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api.protocol import Property
from .coordinator import PB20ConfigEntry, PB20Coordinator
from .entity import PB20Entity


@dataclass(frozen=True, kw_only=True)
class PB20SwitchDescription(SwitchEntityDescription):
    """Pair a HA switch with its device property."""

    prop: Property


SWITCHES = (
    PB20SwitchDescription(
        key="child_lock",
        translation_key="child_lock",
        prop=Property.CHILD_LOCK,
        icon="mdi:lock",
        entity_category=EntityCategory.CONFIG,
    ),
    PB20SwitchDescription(
        key="continuous_monitoring",
        translation_key="continuous_monitoring",
        prop=Property.CONTINUOUS_MONITORING,
        icon="mdi:air-filter",
        entity_category=EntityCategory.CONFIG,
    ),
    PB20SwitchDescription(
        key="uvc", translation_key="uvc", prop=Property.UVC, icon="mdi:lightbulb-fluorescent-tube"
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: PB20ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(PB20Switch(entry.runtime_data, description) for description in SWITCHES)


class PB20Switch(PB20Entity, SwitchEntity):
    """Read and set an absolute hardware state."""

    entity_description: PB20SwitchDescription

    def __init__(self, coordinator: PB20Coordinator, description: PB20SwitchDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return getattr(self.coordinator.data, self.entity_description.key)

    @property
    def available(self) -> bool:
        return super().available and self.is_on is not None

    async def _set(self, enabled: bool) -> None:
        await self.coordinator.command(
            lambda: self.coordinator.device.set_switch(self.entity_description.prop, enabled)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)
