"""Integration configuration and UI modes."""

from homeassistant.const import Platform

from .api.protocol import Mode

DOMAIN = "dreame_pb20"
CONF_REGION = "region"
CONF_DEVICE_ID = "device_id"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 30
PLATFORMS = (Platform.FAN, Platform.SENSOR, Platform.SWITCH, Platform.BUTTON)
PRESETS = {"AI Purify": Mode.AI_PURIFY, "Sleep": Mode.SLEEP, "Custom": Mode.CUSTOM}
