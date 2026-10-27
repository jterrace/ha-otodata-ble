"""
Custom integration for Otodata propane tank monitors over Bluetooth LE.

For more details about this integration, please refer to
https://github.com/jterrace/ha-otodata-ble
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # noqa: ARG001
    """Set up an Otodata monitor from a config entry."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # noqa: ARG001
    """Unload a config entry."""
    return True
