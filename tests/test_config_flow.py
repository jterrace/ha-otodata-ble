"""Tests for the Otodata BLE config flow."""

from unittest.mock import patch

import pytest
from home_assistant_bluetooth import BluetoothServiceInfo
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.const import CONF_ADDRESS, CONF_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util.unit_system import (
    METRIC_SYSTEM,
    US_CUSTOMARY_SYSTEM,
    UnitSystem,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.otodata_ble.const import CONF_CAPACITY, DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:01"
OTHER_ADDRESS = "AA:BB:CC:DD:EE:02"

TELEMETRY = bytes.fromhex("4f544f54454c450200c00c0000715406180000ff00000000")


def _service_info(
    address: str = ADDRESS, manufacturer_data: dict[int, bytes] | None = None
) -> BluetoothServiceInfo:
    """Build a passive advertisement as an ESPHome proxy would see it."""
    return BluetoothServiceInfo(
        name=address,
        address=address,
        rssi=-70,
        manufacturer_data={945: TELEMETRY}
        if manufacturer_data is None
        else manufacturer_data,
        service_data={},
        service_uuids=[],
        source="local",
    )


# An iBeacon from the same kind of device: no Otodata manufacturer data.
NOT_OTODATA = _service_info(manufacturer_data={76: bytes.fromhex("0215a4552f9f")})
# Otodata company ID, but not an OTO packet.
UNKNOWN_PACKET = _service_info(manufacturer_data={945: b"XYZ1234" + bytes(17)})


def _patch_discovered(*service_infos: BluetoothServiceInfo):  # noqa: ANN202
    """Patch the devices that Bluetooth has already seen."""
    return patch(
        "custom_components.otodata_ble.config_flow.async_discovered_service_info",
        return_value=list(service_infos),
    )


async def test_bluetooth_discovery(hass: HomeAssistant) -> None:
    """A discovered monitor is set up after the user confirms it."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_service_info()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"
    assert result["description_placeholders"] == {"name": "Otodata EE01"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Otodata EE01"
    assert result["data"] == {}
    assert result["result"].unique_id == ADDRESS


async def test_bluetooth_discovery_already_configured(hass: HomeAssistant) -> None:
    """Discovering a monitor that is already set up aborts."""
    MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_service_info()
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_bluetooth_discovery_already_in_progress(hass: HomeAssistant) -> None:
    """A second discovery of the same monitor aborts while the first is open."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_service_info()
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_service_info()
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_in_progress"


async def test_bluetooth_discovery_not_supported(hass: HomeAssistant) -> None:
    """Discovery aborts for advertisements without an Otodata packet."""
    for service_info in (NOT_OTODATA, UNKNOWN_PACKET):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=service_info
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "not_supported"


async def test_user_step(hass: HomeAssistant) -> None:
    """The user can pick a monitor that Bluetooth has already seen."""
    with _patch_discovered(_service_info()):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADDRESS: ADDRESS}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Otodata EE01"
    assert result["data"] == {}
    assert result["result"].unique_id == ADDRESS


async def test_user_step_no_devices(hass: HomeAssistant) -> None:
    """The user step aborts when no unconfigured monitors have been seen."""
    MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS).add_to_hass(hass)
    with _patch_discovered(_service_info(), NOT_OTODATA, UNKNOWN_PACKET):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_user_step_lists_only_new_monitors(hass: HomeAssistant) -> None:
    """The device list skips configured monitors and other devices."""
    MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS).add_to_hass(hass)
    with _patch_discovered(
        _service_info(), _service_info(OTHER_ADDRESS), NOT_OTODATA, UNKNOWN_PACKET
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    schema = result["data_schema"].schema[CONF_ADDRESS]
    assert schema.container == {OTHER_ADDRESS: "Otodata EE02"}


async def test_user_step_replaces_discovery(hass: HomeAssistant) -> None:
    """Setting up from the user step aborts the open discovery for that monitor."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_service_info()
    )
    assert result["type"] is FlowResultType.FORM

    with _patch_discovered(_service_info()):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADDRESS: ADDRESS}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)


@pytest.mark.parametrize(
    ("units", "unit"), [(US_CUSTOMARY_SYSTEM, "gal"), (METRIC_SYSTEM, "L")]
)
async def test_options_default_unit(
    hass: HomeAssistant, units: UnitSystem, unit: str
) -> None:
    """The unit defaults to the one that goes with Home Assistant's unit system."""
    hass.config.units = units
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS)
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_CAPACITY: 240}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_CAPACITY: 240, CONF_UNIT_OF_MEASUREMENT: unit}


async def test_options_prefilled(hass: HomeAssistant) -> None:
    """The form shows the current options."""
    options = {CONF_CAPACITY: 500, CONF_UNIT_OF_MEASUREMENT: "L"}
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, options=options)
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    suggested = {
        key.schema: key.description["suggested_value"]
        for key in result["data_schema"].schema
    }
    assert suggested == options
