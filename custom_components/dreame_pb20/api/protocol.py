"""Dreame cloud wire format and verified PB20 property addresses."""

from enum import Enum, IntEnum
from hashlib import md5
from itertools import count
from typing import Any

MODEL = "dreame.airp.u2605"
REGIONS = ("cn", "eu", "us", "sg", "kr")
AUTHORIZATION = "Basic ZHJlYW1lX2FwcHYxOkFQXmR2QHpAU1FZVnhOODg="
PASSWORD_SALT = "RAylYC%fmSKp7%Tq"
REQUEST_IDS = count(1)


class Property(Enum):
    """Properties supported by the PB20 firmware."""

    POWER = (2, 1)
    MODE = (2, 3)
    SPEED = (2, 4)
    HUMIDITY = (3, 2)
    TEMPERATURE = (3, 3)
    AIR_QUALITY = (3, 4)
    PM25 = (3, 5)
    PM10 = (3, 6)
    FORMALDEHYDE = (3, 7)
    FILTER_REMAINING = (4, 16)


class Mode(IntEnum):
    """PB20 operating modes."""

    AI_PURIFY = 0
    SLEEP = 2
    CUSTOM = 3


def base_url(region: str) -> str:
    """Select a known cloud region."""
    if region not in REGIONS:
        raise ValueError("Unsupported Dreame region")
    return f"https://{region}.iot.dreame.tech:13267"


def headers(tenant: str, token: str | None = None) -> dict[str, str]:
    """Construct authentication headers without logging credentials."""
    result = {
        "Authorization": AUTHORIZATION,
        "Tenant-Id": tenant,
        "User-Agent": "Dreame_Smarthome/2.1.9 (iPhone; iOS 18.4.1; Scale/3.00)",
    }
    if token is not None:
        result["Dreame-Auth"] = token
    return result


def password_grant(username: str, password: str) -> dict[str, str]:
    """Build the password grant required by the cloud."""
    return {
        "platform": "IOS",
        "scope": "all",
        "grant_type": "password",
        "type": "account",
        "username": username,
        "password": md5((password + PASSWORD_SALT).encode()).hexdigest(),
    }


def command_path(bind_domain: str | None) -> str:
    """Address the device's cloud shard."""
    shard = f"-{bind_domain.split('.')[0]}" if bind_domain else ""
    return f"/dreame-iot-com{shard}/device/sendCommand"


def envelope(device_id: str, method: str, params: Any) -> dict[str, Any]:
    """Use one fresh correlation ID in both RPC envelopes."""
    request_id = next(REQUEST_IDS)
    return {
        "did": device_id,
        "id": request_id,
        "data": {"did": device_id, "id": request_id, "method": method, "params": params},
    }
