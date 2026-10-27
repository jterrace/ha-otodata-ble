"""
Decoder for Otodata BLE advertisements.

Payloads are the manufacturer specific data for company ID 0x03B1 with the
company ID already stripped.
"""

import logging
from dataclasses import dataclass
from enum import Enum

_LOGGER = logging.getLogger(__name__)

_PACKET_PREFIX = b"OTO"
_PACKET_TYPE_LENGTH = 7

# Minimum lengths needed to read the fields we decode.
_INFO_MIN_LENGTH = 21
_TELEMETRY_MIN_LENGTH = 11

_LEVEL_MIN = 0.0
_LEVEL_MAX = 100.0


class PacketType(Enum):
    """Otodata packet types, identified by the payload's first 7 bytes."""

    INFO = b"OTO3281"
    TELEMETRY = b"OTOTELE"
    STATUS = b"OTOSTAT"


@dataclass(frozen=True)
class OtodataInfo:
    """Device information from an OTO3281 packet."""

    serial: int
    model_number: int

    @property
    def model(self) -> str:
        """Return the product model name, e.g. TM6030."""
        return f"TM{self.model_number}"


@dataclass(frozen=True)
class OtodataTelemetry:
    """Telemetry from an OTOTELE packet."""

    level: float


def get_packet_type(payload: bytes) -> PacketType | None:
    """Return the payload's packet type, or None if it isn't one we know."""
    packet_type = payload[:_PACKET_TYPE_LENGTH]
    if len(packet_type) < _PACKET_TYPE_LENGTH or not packet_type.startswith(
        _PACKET_PREFIX
    ):
        _LOGGER.debug("Ignoring non-Otodata payload: %s", payload.hex())
        return None
    try:
        return PacketType(packet_type)
    except ValueError:
        _LOGGER.debug("Ignoring unknown packet type %r: %s", packet_type, payload.hex())
        return None


def parse_info(payload: bytes) -> OtodataInfo | None:
    """Decode an OTO3281 packet, or return None if it's invalid."""
    if not payload.startswith(PacketType.INFO.value) or len(payload) < _INFO_MIN_LENGTH:
        _LOGGER.debug("Ignoring invalid info packet: %s", payload.hex())
        return None
    return OtodataInfo(
        serial=int.from_bytes(payload[7:11], byteorder="little"),
        model_number=int.from_bytes(payload[19:21], byteorder="little"),
    )


def parse_telemetry(payload: bytes) -> OtodataTelemetry | None:
    """Decode an OTOTELE packet, or return None if it's invalid."""
    if (
        not payload.startswith(PacketType.TELEMETRY.value)
        or len(payload) < _TELEMETRY_MIN_LENGTH
    ):
        _LOGGER.debug("Ignoring invalid telemetry packet: %s", payload.hex())
        return None
    level = int.from_bytes(payload[9:11], byteorder="little") / 100
    if not _LEVEL_MIN <= level <= _LEVEL_MAX:
        _LOGGER.debug(
            "Ignoring telemetry packet with out of range level %s: %s",
            level,
            payload.hex(),
        )
        return None
    return OtodataTelemetry(level=level)
