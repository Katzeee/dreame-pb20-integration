"""Dreame PB20 cloud integration."""

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.client import AuthenticationError, CloudClient, CloudError
from .api.device import DeviceInfo, PB20Device
from .api.protocol import MODEL
from .const import CONF_DEVICE_ID, CONF_REGION, PLATFORMS
from .coordinator import PB20ConfigEntry, PB20Coordinator


async def async_setup_entry(hass: HomeAssistant, entry: PB20ConfigEntry) -> bool:
    """Resolve the configured PB20 and fetch its first complete snapshot."""
    client = CloudClient(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_REGION],
    )
    try:
        record = next(
            (
                d
                for d in await client.devices()
                if d.get("model") == MODEL and str(d.get("did")) == entry.data[CONF_DEVICE_ID]
            ),
            None,
        )
        if record is None:
            raise ConfigEntryNotReady("The configured PB20 is absent from this Dreame account")
        device = PB20Device(client, DeviceInfo.from_record(record))
    except AuthenticationError as err:
        raise ConfigEntryAuthFailed("Dreame authentication rejected") from err
    except CloudError as err:
        raise ConfigEntryNotReady(str(err)) from err
    coordinator = PB20Coordinator(hass, entry, device)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: PB20ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PB20ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
