"""PB20 state decoding and serialized device operations."""

import asyncio
import math
from dataclasses import dataclass
from typing import Any

from .client import CloudClient, CloudError
from .protocol import Mode, Property


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """Metadata needed to address one PB20."""

    device_id: str
    name: str
    bind_domain: str | None
    firmware: str | None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "DeviceInfo":
        device_id = record.get("did")
        if device_id is None:
            raise CloudError("Device metadata contains no device ID")
        return cls(
            str(device_id),
            record.get("customName") or "Air Purifier PB20",
            record.get("bindDomain"),
            record.get("ver"),
        )


@dataclass(frozen=True, slots=True)
class State:
    """One complete read, with missing or invalid properties left unknown."""

    power: bool | None
    mode: Mode | None
    speed: int | None
    humidity: float | None
    temperature: float | None
    air_quality: str | None
    pm25: float | None
    pm10: float | None
    formaldehyde: float | None
    filter_remaining: float | None
    filter_days_remaining: float | None
    aq: float | None
    child_lock: bool | None
    continuous_monitoring: bool | None
    uvc: bool | None

    @classmethod
    def decode(cls, values: dict[Property, Any]) -> "State":
        def number(prop: Property, minimum: float, maximum: float) -> float | None:
            value = values.get(prop)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            return value if math.isfinite(value) and minimum <= value <= maximum else None

        def switch(prop: Property) -> bool | None:
            value = values.get(prop)
            return (
                bool(value) if isinstance(value, (bool, int, float)) and value in (0, 1) else None
            )

        raw_power = number(Property.POWER, 1, 2)
        raw_mode = number(Property.MODE, 0, 3)
        raw_speed = number(Property.SPEED, 1, 10)
        hcho = number(Property.FORMALDEHYDE, 0, 1_000_000)
        return cls(
            power={1: True, 2: False}.get(raw_power),
            mode=Mode(raw_mode) if raw_mode in set(Mode) else None,
            speed=int(raw_speed) if raw_speed is not None and int(raw_speed) == raw_speed else None,
            humidity=number(Property.HUMIDITY, 0, 100),
            temperature=number(Property.TEMPERATURE, -50, 100),
            air_quality={1: "excellent", 2: "good", 3: "average", 4: "poor"}.get(
                number(Property.AIR_QUALITY, 1, 4)
            ),
            pm25=number(Property.PM25, 0, 1_000_000),
            pm10=number(Property.PM10, 0, 1_000_000),
            formaldehyde=hcho / 1000 if hcho is not None else None,
            filter_remaining=number(Property.FILTER_REMAINING, 0, 100),
            filter_days_remaining=number(Property.FILTER_DAYS_REMAINING, 0, 10000),
            aq=number(Property.AQ, 0, 100),
            child_lock=switch(Property.CHILD_LOCK),
            continuous_monitoring=switch(Property.CONTINUOUS_MONITORING),
            uvc=switch(Property.UVC),
        )


class PB20Device:
    """Keep a control sequence and its readback inside the same device lock."""

    def __init__(self, client: CloudClient, info: DeviceInfo) -> None:
        self.client = client
        self.info = info
        self.lock = asyncio.Lock()

    async def _read(self) -> State:
        state = State.decode(await self.client.read(self.info.device_id, self.info.bind_domain))
        if state.power is None:
            raise CloudError("PB20 reports an unknown power state")
        return state

    async def refresh(self) -> State:
        async with self.lock:
            return await self._read()

    async def set_switch(self, prop: Property, enabled: bool) -> State:
        """Apply one supported hardware setting."""
        if prop not in {Property.CHILD_LOCK, Property.CONTINUOUS_MONITORING, Property.UVC}:
            raise ValueError("Unsupported PB20 switch")
        async with self.lock:
            await self.client.write(
                self.info.device_id, self.info.bind_domain, [(prop, int(enabled))]
            )
            return await self._read()

    async def reset_filter(self) -> State:
        """Reset the all-in-one filter life after replacement."""
        async with self.lock:
            await self.client.action(self.info.device_id, self.info.bind_domain, 4, 8)
            return await self._read()

    async def configure(
        self, *, power: bool | None = None, mode: Mode | None = None, speed: int | None = None
    ) -> State:
        """Apply absolute settings and return the device's reported state."""
        if speed is not None:
            if isinstance(speed, bool) or not isinstance(speed, int) or not 1 <= speed <= 10:
                raise ValueError("PB20 speed must be an integer from 1 to 10")
            if mode is not None and mode != Mode.CUSTOM:
                raise ValueError("A manual speed requires Custom mode")
            mode = Mode.CUSTOM
        async with self.lock:
            if power is not None:
                await self.client.power(self.info.device_id, self.info.bind_domain, power)
            writes = []
            if mode is not None:
                writes.append((Property.MODE, int(mode)))
            if speed is not None:
                writes.append((Property.SPEED, speed))
            if writes:
                await self.client.write(self.info.device_id, self.info.bind_domain, writes)
            return await self._read()
