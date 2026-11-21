"""
Decoder for Otodata BLE advertisements.

Payloads are the manufacturer specific data for company ID 0x03B1 with the
company ID already stripped.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

_LOGGER = logging.getLogger(__name__)

_PACKET_PREFIX = b"OTO"
_PACKET_TYPE_LENGTH = 7

# Minimum lengths needed to read the fields we decode. Some monitors send a
# short info packet that stops before the model number.
_INFO_MIN_LENGTH = 11
_INFO_WITH_MODEL_MIN_LENGTH = 21
_TELEMETRY_MIN_LENGTH = 11

_LEVEL_MIN = 0.0
_LEVEL_MAX = 100.0

# The level in the rotating local name, e.g. "level: 80 % vertical". The name
# can be cut short to fit the scan response, e.g. "level: 80 % vertica".
_NAME_LEVEL_PATTERN = re.compile(r"level:\s*(\d+(?:\.\d+)?)\s*%")


class PacketType(Enum):
    """Otodata packet types, identified by the payload's first 7 bytes."""

    INFO = b"OTO3281"
    TELEMETRY = b"OTOTELE"
    STATUS = b"OTOSTAT"


@dataclass(frozen=True)
class OtodataInfo:
    """Device information from an OTO3281 packet."""

    serial: int
    # None for monitors whose short info packet has no model number.
    model_number: int | None

    @property
    def model(self) -> str | None:
        """Return the product model name, e.g. TM6030, if known."""
        if self.model_number is None:
            return None
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
    model_number = None
    if len(payload) >= _INFO_WITH_MODEL_MIN_LENGTH:
        model_number = int.from_bytes(payload[19:21], byteorder="little")
    return OtodataInfo(
        serial=int.from_bytes(payload[7:11], byteorder="little"),
        model_number=model_number,
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


def parse_name_level(name: str | None) -> OtodataTelemetry | None:
    """
    Decode the tank level from the local name, or return None if it has none.

    Monitors that send no OTOTELE packets only report the level in the
    rotating name of their scan response, rounded and lagging the real level.
    """
    if not name or not (match := _NAME_LEVEL_PATTERN.match(name)):
        return None
    level = float(match.group(1))
    if not _LEVEL_MIN <= level <= _LEVEL_MAX:
        _LOGGER.debug("Ignoring out of range level in name: %r", name)
        return None
    return OtodataTelemetry(level=level)
