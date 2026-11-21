"""Turn Bluetooth advertisements into Otodata updates."""

import logging
from dataclasses import dataclass

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothProcessorCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import UNDEFINED

from .const import MANUFACTURER, MANUFACTURER_ID
from .parser import (
    OtodataInfo,
    OtodataTelemetry,
    PacketType,
    get_packet_type,
    parse_info,
    parse_name_level,
    parse_telemetry,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OtodataUpdate:
    """
    What one advertisement told us.

    Each advertisement carries one packet type, so usually at most one of
    info and telemetry is set. Monitors with a short info packet are the
    exception: their level comes from the local name, alongside the info.
    """

    rssi: int
    info: OtodataInfo | None = None
    telemetry: OtodataTelemetry | None = None


type OtodataCoordinator = PassiveBluetoothProcessorCoordinator[OtodataUpdate | None]
type OtodataConfigEntry = ConfigEntry[OtodataCoordinator]


def parse_service_info(service_info: BluetoothServiceInfoBleak) -> OtodataUpdate | None:
    """Decode an advertisement, or return None if it has no Otodata packet."""
    payload = service_info.manufacturer_data.get(MANUFACTURER_ID)
    if payload is None:
        _LOGGER.debug(
            "Ignoring advertisement from %s without Otodata data: %s",
            service_info.address,
            service_info.manufacturer_data,
        )
        return None
    # Log every payload so captures can be used to decode more fields.
    _LOGGER.debug(
        "Advertisement from %s rssi=%s name=%r: %s",
        service_info.address,
        service_info.rssi,
        service_info.name,
        payload.hex(),
    )
    match get_packet_type(payload):
        case PacketType.INFO:
            info = parse_info(payload)
            telemetry = None
            # Monitors with a short info packet send no OTOTELE packets; their
            # level is only in the name. Other monitors' OTOTELE level is more
            # precise and more recent, so their name is ignored.
            if info is not None and info.model_number is None:
                telemetry = parse_name_level(service_info.name)
            return OtodataUpdate(rssi=service_info.rssi, info=info, telemetry=telemetry)
        case PacketType.TELEMETRY:
            return OtodataUpdate(
                rssi=service_info.rssi, telemetry=parse_telemetry(payload)
            )
        case PacketType.STATUS:
            # Not decoded yet; still counts for signal strength.
            return OtodataUpdate(rssi=service_info.rssi)
        case None:
            return None


@callback
def async_update_device_info(
    hass: HomeAssistant, entry: OtodataConfigEntry, info: OtodataInfo
) -> None:
    """
    Record the model and serial in the device registry.

    They arrive in their own packet, often after the sensors exist, so they
    can't be set when the sensors create the device.
    """
    assert entry.unique_id is not None  # noqa: S101
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_BLUETOOTH, entry.unique_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=info.model or UNDEFINED,
        serial_number=str(info.serial),
    )
