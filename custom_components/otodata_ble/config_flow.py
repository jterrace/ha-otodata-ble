"""Config flow for Otodata BLE."""

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, MANUFACTURER_ID
from .parser import get_packet_type


def _is_otodata(discovery_info: BluetoothServiceInfoBleak) -> bool:
    """Return True if the advertisement carries an Otodata packet."""
    payload = discovery_info.manufacturer_data.get(MANUFACTURER_ID)
    return payload is not None and get_packet_type(payload) is not None


def _title(discovery_info: BluetoothServiceInfoBleak) -> str:
    """
    Return a title for the device.

    The serial and model usually aren't known yet at discovery, so use the end
    of the address to tell monitors apart.
    """
    return f"Otodata {discovery_info.address.replace(':', '')[-4:].upper()}"


class OtodataConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Otodata BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, str] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a device found by Bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        if not _is_otodata(discovery_info):
            return self.async_abort(reason="not_supported")
        self._discovery_info = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm setup of a discovered device."""
        assert self._discovery_info is not None  # noqa: S101
        title = _title(self._discovery_info)
        if user_input is not None:
            return self.async_create_entry(title=title, data={})

        self._set_confirm_only()
        placeholders = {"name": title}
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="bluetooth_confirm", description_placeholders=placeholders
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick from devices that have already been discovered."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._discovered_devices[address], data={}
            )

        current_addresses = self._async_current_ids(include_ignore=False)
        for discovery_info in async_discovered_service_info(
            self.hass, connectable=False
        ):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue
            if _is_otodata(discovery_info):
                self._discovered_devices[address] = _title(discovery_info)

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._discovered_devices)}
            ),
        )
