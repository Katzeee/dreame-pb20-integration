"""Account authentication and PB20 selection."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.client import AuthenticationError, CloudClient, CloudError
from .api.device import DeviceInfo
from .api.protocol import MODEL, REGIONS
from .const import (
    CONF_DEVICE_ID,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


def account_schema(defaults: dict[str, Any], *, include_region: bool = True) -> vol.Schema:
    """Mask the password and offer explicit cloud regions."""
    fields = {
        vol.Required(
            CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")
        ): selector.TextSelector(),
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
    if include_region:
        fields[vol.Required(CONF_REGION, default=defaults.get(CONF_REGION, "cn"))] = (
            selector.SelectSelector(
                selector.SelectSelectorConfig(options=list(REGIONS), translation_key="region")
            )
        )
    return vol.Schema(fields)


class PB20ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one PB20 per entry without requiring another integration."""

    VERSION = 1

    def __init__(self) -> None:
        self._account: dict[str, Any] = {}
        self._devices: dict[str, DeviceInfo] = {}

    async def _discover(self, account: dict[str, Any]) -> str | None:
        client = CloudClient(
            async_get_clientsession(self.hass),
            account[CONF_USERNAME],
            account[CONF_PASSWORD],
            account[CONF_REGION],
        )
        try:
            records = await client.devices()
            self._devices = {
                str(d["did"]): DeviceInfo.from_record(d)
                for d in records
                if d.get("model") == MODEL and d.get("did") is not None
            }
        except AuthenticationError:
            return "invalid_auth"
        except CloudError:
            return "cannot_connect"
        return None if self._devices else "no_devices"

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            error = await self._discover(user_input)
            if error is None:
                self._account = user_input
                return await self.async_step_device()
            errors["base"] = error
        return self.async_show_form(
            step_id="user", data_schema=account_schema(user_input or {}), errors=errors
        )

    async def async_step_device(self, user_input=None):
        errors = {}
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            if device_id in self._devices:
                await self.async_set_unique_id(f"{self._account[CONF_REGION]}:{device_id}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=self._devices[device_id].name,
                    data={**self._account, CONF_DEVICE_ID: device_id},
                )
            errors["base"] = "device_unavailable"
        options = [
            {"value": key, "label": f"{info.name} ({key[-4:]})"}
            for key, info in self._devices.items()
        ]
        return self.async_show_form(
            step_id="device",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options)
                    )
                }
            ),
        )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            account = {**entry.data, **user_input}
            error = await self._discover(account)
            if error is None and entry.data[CONF_DEVICE_ID] not in self._devices:
                error = "device_unavailable"
            if error is None:
                return self.async_update_reload_and_abort(entry, data=account)
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            errors=errors,
            data_schema=account_schema(entry.data, include_region=False),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PB20OptionsFlow()


class PB20OptionsFlow(config_entries.OptionsFlow):
    """Set a bounded cloud polling interval."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=interval): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=15,
                            max=300,
                            step=1,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
