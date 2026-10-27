"""
Custom integration for Otodata propane tank monitors over Bluetooth LE.

For more details about this integration, please refer to
https://github.com/jterrace/ha-otodata-ble
"""

import logging

from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_set_fallback_availability_interval,
)
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothProcessorCoordinator,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import (
    OtodataConfigEntry,
    OtodataUpdate,
    async_update_device_info,
    parse_service_info,
)

_LOGGER = logging.getLogger(__name__)

_PLATFORMS = [Platform.SENSOR]

# The monitor sleeps for hours between broadcasts. Bluetooth uses this until it
# has learned the monitor's own advertising interval.
_FALLBACK_AVAILABILITY_INTERVAL = 6 * 60 * 60


async def async_setup_entry(hass: HomeAssistant, entry: OtodataConfigEntry) -> bool:
    """Set up an Otodata monitor from a config entry."""
    address = entry.unique_id
    assert address is not None  # noqa: S101

    def update_method(service_info: BluetoothServiceInfoBleak) -> OtodataUpdate | None:
        update = parse_service_info(service_info)
        if update is not None and update.info is not None:
            async_update_device_info(hass, entry, update.info)
        return update

    async_set_fallback_availability_interval(
        hass, address, _FALLBACK_AVAILABILITY_INTERVAL
    )
    entry.runtime_data = PassiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.PASSIVE,
        update_method=update_method,
    )
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    # Start only after the platforms have subscribed, so no update is missed.
    entry.async_on_unload(entry.runtime_data.async_start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OtodataConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
