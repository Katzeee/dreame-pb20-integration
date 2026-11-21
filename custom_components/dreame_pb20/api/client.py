"""Asynchronous authenticated Dreame cloud transport."""

import asyncio
from collections.abc import Sequence
from time import monotonic
from typing import Any

import aiohttp

from . import protocol

TIMEOUT = aiohttp.ClientTimeout(total=15)
TOKEN_PATH = "/dreame-auth/oauth/token"


class CloudError(Exception):
    """The cloud request fails or its response is invalid."""


class AuthenticationError(CloudError):
    """The account needs to authenticate again."""


class CommandError(CloudError):
    """The device rejects a command."""


class CloudClient:
    """Manage tokens and device RPCs using a caller-owned HTTP session."""

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str, region: str
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._base_url = protocol.base_url(region)
        self._region = region
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._expires = 0.0
        self._tenant = "000000"
        self._auth_lock = asyncio.Lock()

    async def _request(
        self,
        path: str,
        *,
        form: dict | None = None,
        payload: dict | None = None,
        token: str | None = None,
    ) -> dict:
        request_headers = protocol.headers(self._tenant, token)
        if self._region == "cn":
            request_headers["Dreame-Rlc"] = "1c80b3787b2266776bcdc481f37d8fa42ba10a30af81a6df-1"
        try:
            async with self._session.post(
                self._base_url + path,
                headers=request_headers,
                data=form,
                json=payload,
                timeout=TIMEOUT,
            ) as response:
                if response.status in (401, 403) or (form and response.status == 400):
                    raise AuthenticationError("Dreame authentication rejected")
                if response.status != 200:
                    raise CloudError(f"Dreame HTTP status {response.status}")
                result = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise CloudError("Unable to read a valid Dreame cloud response") from err
        if not isinstance(result, dict):
            raise CloudError("Unexpected cloud response format")
        return result

    async def authenticate(self, rejected_token: str | None = None) -> None:
        """Serialize renewal and reuse a token refreshed by another caller."""
        async with self._auth_lock:
            if self._token and self._expires > monotonic() and self._token != rejected_token:
                return
            result: dict = {}
            if self._refresh_token:
                try:
                    result = await self._request(
                        TOKEN_PATH,
                        form={
                            "platform": "IOS",
                            "scope": "all",
                            "grant_type": "refresh_token",
                            "refresh_token": self._refresh_token,
                        },
                    )
                except AuthenticationError:
                    self._refresh_token = None
            if not result.get("access_token"):
                result = await self._request(
                    TOKEN_PATH, form=protocol.password_grant(self._username, self._password)
                )
            token = result.get("access_token")
            if not isinstance(token, str) or not token:
                raise AuthenticationError("Dreame does not issue an access token")
            self._token = token
            self._refresh_token = result.get("refresh_token")
            self._tenant = result.get("tenant_id") or "000000"
            try:
                lifetime = float(result.get("expires_in", 3600))
            except (TypeError, ValueError):
                lifetime = 3600
            self._expires = monotonic() + max(1, lifetime - 60)

    async def _post(self, path: str, payload: dict) -> dict:
        await self.authenticate()
        token = self._token
        try:
            return await self._request(path, payload=payload, token=token)
        except AuthenticationError:
            await self.authenticate(rejected_token=token)
        return await self._request(path, payload=payload, token=self._token)

    async def devices(self) -> list[dict[str, Any]]:
        """List devices bound to the account."""
        result = await self._post("/dreame-user-iot/iotuserbind/device/listV2", {})
        try:
            devices = result["data"]["page"]["records"]
            if result.get("code") == 0 and isinstance(devices, list):
                return [d for d in devices if isinstance(d, dict)]
        except (KeyError, TypeError):
            pass
        raise CloudError("Unable to retrieve the Dreame device list")

    async def _command(
        self, device_id: str, bind_domain: str | None, method: str, params: Any
    ) -> Any:
        result = await self._post(
            protocol.command_path(bind_domain), protocol.envelope(device_id, method, params)
        )
        if result.get("code") != 0:
            raise CloudError(f"Dreame RPC fails with code {result.get('code')}")
        data = result.get("data")
        if not isinstance(data, dict) or "result" not in data:
            raise CloudError("Dreame RPC contains no device response")
        return data["result"]

    async def read(self, device_id: str, bind_domain: str | None) -> dict[protocol.Property, Any]:
        """Read the verified properties in one ten-property request."""
        result = await self._command(
            device_id,
            bind_domain,
            "get_properties",
            [{"did": device_id, "siid": p.value[0], "piid": p.value[1]} for p in protocol.Property],
        )
        if not isinstance(result, list):
            raise CloudError("Device property response is not a list")
        values = {}
        for item in result:
            if not isinstance(item, dict) or item.get("code") != 0 or "value" not in item:
                continue
            if str(item.get("did")) != device_id:
                raise CloudError("Device property response belongs to another device")
            try:
                prop = protocol.Property((item.get("siid"), item.get("piid")))
            except ValueError:
                continue
            values[prop] = item["value"]
        if protocol.Property.POWER not in values:
            raise CloudError("Device does not report its power state")
        return values

    async def write(
        self,
        device_id: str,
        bind_domain: str | None,
        values: Sequence[tuple[protocol.Property, int]],
    ) -> None:
        """Require a successful response for every requested property."""
        params = [
            {"did": device_id, "siid": prop.value[0], "piid": prop.value[1], "value": value}
            for prop, value in values
        ]
        result = await self._command(device_id, bind_domain, "set_properties", params)
        expected = {prop.value for prop, _ in values}
        if not isinstance(result, list) or len(result) != len(expected):
            raise CommandError("Incomplete property write response")
        answered = set()
        for item in result:
            if not isinstance(item, dict) or item.get("code") != 0:
                raise CommandError("PB20 rejects the requested property")
            if str(item.get("did")) != device_id:
                raise CommandError("Property write response belongs to another device")
            answered.add((item.get("siid"), item.get("piid")))
        if answered != expected:
            raise CommandError("Property write response does not match the request")

    async def power(self, device_id: str, bind_domain: str | None, on: bool) -> None:
        """Set the desired power state using PB20's parameterized action."""
        result = await self._command(
            device_id,
            bind_domain,
            "action",
            {
                "did": device_id,
                "siid": 2,
                "aiid": 1,
                "in": [{"piid": 1, "value": int(on)}],
            },
        )
        if not isinstance(result, dict) or result.get("code") != 0:
            raise CommandError("PB20 rejects the power action")
        if (str(result.get("did")), result.get("siid"), result.get("aiid")) != (device_id, 2, 1):
            raise CommandError("Power action response does not match the request")
