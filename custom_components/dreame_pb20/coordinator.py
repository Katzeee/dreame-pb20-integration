"""Home Assistant polling and command error handling."""

import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import AuthenticationError, CloudError
from .api.device import PB20Device, State
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class PB20Coordinator(DataUpdateCoordinator[State]):
    """Share one device snapshot across entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, device: PB20Device) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
            always_update=False,
        )
        self.device = device

    async def _async_update_data(self) -> State:
        try:
            return await self.device.refresh()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed("Dreame authentication rejected") from err
        except CloudError as err:
            raise UpdateFailed(str(err)) from err

    async def command(self, operation: Callable[[], Awaitable[State]]) -> None:
        """Publish only reported state; surface command failures to the caller."""
        try:
            await operation()
        except AuthenticationError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="authentication_failed"
            ) from err
        except (CloudError, ValueError) as err:
            # Refresh also reconciles any successful part of a multi-step operation.
            await self.async_refresh()
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
        # A coordinator refresh publishes a fresh snapshot through its own update lock.
        # Publishing a command's earlier readback can overwrite a later poll or command.
        await self.async_refresh()


type PB20ConfigEntry = ConfigEntry[PB20Coordinator]
