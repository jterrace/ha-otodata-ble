"""Tests for the Otodata BLE sensors, fed through Home Assistant's Bluetooth stack."""

import logging
import time

import pytest
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_get_advertisement_callback,
    async_get_fallback_availability_interval,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.otodata_ble.const import DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:01"

INFO = bytes.fromhex("4f544f333238319d7c38010d1210036404021a8e170004")
TELEMETRY = bytes.fromhex("4f544f54454c450200c00c0000715406180000ff00000000")
TELEMETRY_OUT_OF_RANGE = b"OTOTELE\x02\x00\xff\xff" + bytes(13)
STATUS = bytes.fromhex("4f544f5354415401730073008abc040007b7000000000000")

LEVEL_ENTITY = "sensor.otodata_ee01_tank_level"
SIGNAL_ENTITY = "sensor.otodata_ee01_signal_strength"


def _inject(
    hass: HomeAssistant, manufacturer_data: dict[int, bytes], rssi: int = -70
) -> None:
    """Deliver an advertisement as if a passive proxy had just heard it."""
    advertisement = AdvertisementData(
        local_name=None,
        manufacturer_data=manufacturer_data,
        service_data={},
        service_uuids=[],
        tx_power=None,
        rssi=rssi,
        platform_data=(),
    )
    async_get_advertisement_callback(hass)(
        BluetoothServiceInfoBleak(
            name=ADDRESS,
            address=ADDRESS,
            rssi=rssi,
            manufacturer_data=manufacturer_data,
            service_data={},
            service_uuids=[],
            source="local",
            device=BLEDevice(ADDRESS, None, {}),
            advertisement=advertisement,
            connectable=False,
            time=time.monotonic(),
            tx_power=None,
        )
    )


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    """Set up a config entry for one monitor."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, title="Otodata EE01")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _device(hass: HomeAssistant) -> dr.DeviceEntry | None:
    """Return the monitor's device, looked up by its Bluetooth address."""
    return dr.async_get(hass).async_get_device(
        connections={(dr.CONNECTION_BLUETOOTH, ADDRESS)}
    )


@pytest.mark.usefixtures("entry")
async def test_telemetry(hass: HomeAssistant) -> None:
    """A telemetry packet creates the tank level sensor."""
    _inject(hass, {945: TELEMETRY})
    await hass.async_block_till_done()

    state = hass.states.get(LEVEL_ENTITY)
    assert state is not None
    assert float(state.state) == pytest.approx(32.64)
    assert state.attributes["unit_of_measurement"] == PERCENTAGE
    assert state.attributes["state_class"] == "measurement"
    assert state.attributes["friendly_name"] == "Otodata EE01 Tank level"


@pytest.mark.usefixtures("entry")
async def test_signal_strength_disabled_by_default(hass: HomeAssistant) -> None:
    """The signal strength sensor exists but is disabled until the user enables it."""
    _inject(hass, {945: STATUS})
    await hass.async_block_till_done()

    entity = er.async_get(hass).async_get(SIGNAL_ENTITY)
    assert entity is not None
    assert entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert entity.entity_category is er.EntityCategory.DIAGNOSTIC
    assert hass.states.get(LEVEL_ENTITY) is None


@pytest.mark.usefixtures("entry")
async def test_device_info_after_sensors(hass: HomeAssistant) -> None:
    """An info packet arriving after the sensors adds the model and serial."""
    _inject(hass, {945: TELEMETRY})
    await hass.async_block_till_done()
    device = _device(hass)
    assert device is not None
    assert device.name == "Otodata EE01"
    assert device.manufacturer == "Otodata"
    assert device.model is None

    _inject(hass, {945: INFO})
    await hass.async_block_till_done()
    device = _device(hass)
    assert device is not None
    assert device.model == "TM6030"
    assert device.serial_number == "20479133"
    assert device.name == "Otodata EE01"


async def test_device_info_before_sensors(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """An info packet arriving first still leaves one device with the sensors on it."""
    _inject(hass, {945: INFO})
    await hass.async_block_till_done()
    _inject(hass, {945: TELEMETRY})
    await hass.async_block_till_done()

    device = _device(hass)
    assert device is not None
    assert device.model == "TM6030"
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert devices == [device]
    entity = er.async_get(hass).async_get(LEVEL_ENTITY)
    assert entity is not None
    assert entity.device_id == device.id


@pytest.mark.usefixtures("entry")
async def test_user_device_name_kept(hass: HomeAssistant) -> None:
    """A later info packet doesn't undo a name the user gave the device."""
    _inject(hass, {945: TELEMETRY})
    await hass.async_block_till_done()
    device = _device(hass)
    assert device is not None
    dr.async_get(hass).async_update_device(device.id, name_by_user="Big tank")

    _inject(hass, {945: INFO})
    await hass.async_block_till_done()
    device = _device(hass)
    assert device is not None
    assert device.name_by_user == "Big tank"


@pytest.mark.usefixtures("entry")
async def test_invalid_telemetry_keeps_last_level(hass: HomeAssistant) -> None:
    """An out-of-range level is ignored and the last good level stays."""
    _inject(hass, {945: TELEMETRY})
    await hass.async_block_till_done()
    _inject(hass, {945: TELEMETRY_OUT_OF_RANGE})
    await hass.async_block_till_done()

    state = hass.states.get(LEVEL_ENTITY)
    assert state is not None
    assert float(state.state) == pytest.approx(32.64)


@pytest.mark.parametrize(
    "manufacturer_data",
    [
        pytest.param({76: bytes.fromhex("0215a4552f9f")}, id="not-otodata"),
        pytest.param({945: b"OTOXXXX" + bytes(17)}, id="unknown-packet"),
    ],
)
async def test_ignored_advertisements(
    hass: HomeAssistant, entry: MockConfigEntry, manufacturer_data: dict[int, bytes]
) -> None:
    """Advertisements without a known Otodata packet create no sensors."""
    _inject(hass, manufacturer_data)
    await hass.async_block_till_done()
    assert not er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)


@pytest.mark.usefixtures("entry")
async def test_payload_debug_logged(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Every Otodata payload is debug logged with its hex."""
    with caplog.at_level(logging.DEBUG, logger="custom_components.otodata_ble"):
        for payload in (INFO, TELEMETRY, STATUS):
            _inject(hass, {945: payload})
            await hass.async_block_till_done()
    for payload in (INFO, TELEMETRY, STATUS):
        assert payload.hex() in caplog.text


@pytest.mark.usefixtures("entry")
async def test_fallback_availability_interval(hass: HomeAssistant) -> None:
    """Until an interval is learned, the monitor may go hours between broadcasts."""
    assert async_get_fallback_availability_interval(hass, ADDRESS) == 6 * 60 * 60


async def test_unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """The entry unloads cleanly."""
    _inject(hass, {945: TELEMETRY})
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
