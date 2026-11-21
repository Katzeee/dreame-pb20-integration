"""Power, operating mode, and ten-level custom speed."""

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api.protocol import Mode
from .const import PRESETS
from .coordinator import PB20ConfigEntry
from .entity import PB20Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: PB20ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([PB20Fan(entry.runtime_data)])


class PB20Fan(PB20Entity, FanEntity):
    """Represent the purifier as its primary fan entity."""

    _attr_name = None
    _attr_icon = "mdi:air-purifier"
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = list(PRESETS)
    _attr_speed_count = 10

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "fan")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.power

    @property
    def percentage(self) -> int | None:
        state = self.coordinator.data
        if state.power is False:
            return 0
        if state.mode == Mode.CUSTOM and state.speed is not None:
            return state.speed * 10
        return None

    @property
    def preset_mode(self) -> str | None:
        return next(
            (name for name, mode in PRESETS.items() if mode == self.coordinator.data.mode), None
        )

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any
    ) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        mode = PRESETS[preset_mode] if preset_mode is not None else None
        speed = math.ceil(percentage / 10) if percentage is not None else None
        await self.coordinator.command(
            lambda: self.coordinator.device.configure(power=True, mode=mode, speed=speed)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.command(lambda: self.coordinator.device.configure(power=False))

    async def async_set_percentage(self, percentage: int) -> None:
        await self.async_turn_on(percentage=percentage)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.coordinator.command(
            lambda: self.coordinator.device.configure(mode=PRESETS[preset_mode])
        )
