"""Tests for the Otodata payload parser, using real captured payloads."""

import logging

import pytest

from custom_components.otodata_ble.parser import (
    OtodataInfo,
    OtodataTelemetry,
    PacketType,
    get_packet_type,
    parse_info,
    parse_name_level,
    parse_telemetry,
)

# TM6030, serial 20479133
INFO_TM6030 = "4f544f333238319d7c38010d1210036404021a8e170004"
# Second-hand sample from another monitor: TM5040, serial 29122704
INFO_TM5040 = "4f544f333238319060bc011018210384060304b0130205"
# Short info packet with no model number, serial 21004997. This monitor sends
# no OTOTELE packets; its level is only in the local name.
INFO_SHORT = "4f544f33323831c58240010d12100170"

TELEMETRY = [
    ("4f544f54454c450200121d0005703606180000ff00000000", 74.42),
    ("4f544f54454c4502000f1d0005703606180000ff00000000", 74.39),
    ("4f544f54454c450200c00c0000715406180000ff00000000", 32.64),
    ("4f544f54454c450200be0c0000715406180000ff00000000", 32.62),
    ("4f544f54454c450200480c0000715a06180000ff00000000", 31.44),
    ("4f544f54454c450200490c0000716e06180000ff00000000", 31.45),
    ("4f544f54454c450200490c0000717006180000ff00000000", 31.45),
    ("4f544f54454c450200490c0000717306180000ff00000000", 31.45),
    ("4f544f54454c450200490c0000717706180000ff00000000", 31.45),
]

STATUS = [
    "4f544f5354415401730073008abc040007b7000000000000",
    "4f544f5354415401750075008abc040007b7000000000000",
    "4f544f53544154015f155f158abc040007b3000000000000",
    "4f544f53544154015a015a018abc040007b3000000000000",
    "4f544f5354415401ec03ec038abc040007b3000000000000",
    "4f544f5354415401940f940f8abc040007b3000000000000",
    "4f544f5354415401890089008abc040007b6000000000000",
    "4f544f5354415401430443048abc040007b6000000000000",
    "4f544f53544154012c052c058abc040007b6000000000000",
    "4f544f5354415401b309b3098abc040007b6000000000000",
]


@pytest.mark.parametrize(
    ("payload", "packet_type"),
    [
        (INFO_TM6030, PacketType.INFO),
        (INFO_TM5040, PacketType.INFO),
        (INFO_SHORT, PacketType.INFO),
        *((payload, PacketType.TELEMETRY) for payload, _ in TELEMETRY),
        *((payload, PacketType.STATUS) for payload in STATUS),
    ],
)
def test_get_packet_type(payload: str, packet_type: PacketType) -> None:
    """Real captured payloads are classified as the right packet type."""
    assert get_packet_type(bytes.fromhex(payload)) is packet_type


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"OTO", id="prefix-only"),
        pytest.param(b"OTOTEL", id="short-type"),
        pytest.param(b"\x02\x15\xa4U/\x9fC\x17N\x99", id="not-otodata"),
        pytest.param(b"OTOXXXX" + bytes(17), id="unknown-type"),
    ],
)
def test_get_packet_type_unknown(
    payload: bytes, caplog: pytest.LogCaptureFixture
) -> None:
    """Non-Otodata and unknown payloads return None and log their hex."""
    with caplog.at_level(logging.DEBUG):
        assert get_packet_type(payload) is None
    assert payload.hex() in caplog.text


@pytest.mark.parametrize(
    ("payload", "serial", "model_number", "model"),
    [
        (INFO_TM6030, 20479133, 6030, "TM6030"),
        (INFO_TM5040, 29122704, 5040, "TM5040"),
        pytest.param(INFO_SHORT, 21004997, None, None, id="short"),
    ],
)
def test_parse_info(
    payload: str, serial: int, model_number: int | None, model: str | None
) -> None:
    """Info packets decode to the right serial number and model."""
    info = parse_info(bytes.fromhex(payload))
    assert info == OtodataInfo(serial=serial, model_number=model_number)
    assert info.model == model


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(bytes.fromhex(INFO_TM6030)[:10], id="truncated"),
        pytest.param(bytes.fromhex(TELEMETRY[0][0]), id="wrong-type"),
        pytest.param(b"", id="empty"),
    ],
)
def test_parse_info_invalid(payload: bytes, caplog: pytest.LogCaptureFixture) -> None:
    """Invalid info payloads return None and log their hex."""
    with caplog.at_level(logging.DEBUG):
        assert parse_info(payload) is None
    assert payload.hex() in caplog.text


@pytest.mark.parametrize(("payload", "level"), TELEMETRY)
def test_parse_telemetry(payload: str, level: float) -> None:
    """Real telemetry packets decode to the right tank level."""
    assert parse_telemetry(bytes.fromhex(payload)) == OtodataTelemetry(level=level)


@pytest.mark.parametrize(
    ("raw", "level"),
    [
        pytest.param(b"\x00\x00", 0.0, id="empty-tank"),
        pytest.param(b"\x10\x27", 100.0, id="full-tank"),  # 10000
    ],
)
def test_parse_telemetry_bounds(raw: bytes, level: float) -> None:
    """Levels of exactly 0% and 100% are accepted."""
    payload = b"OTOTELE\x02\x00" + raw + bytes(13)
    assert parse_telemetry(payload) == OtodataTelemetry(level=level)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(bytes.fromhex(TELEMETRY[0][0])[:10], id="truncated"),
        pytest.param(bytes.fromhex(INFO_TM6030), id="wrong-type"),
        pytest.param(b"", id="empty"),
        pytest.param(b"OTOTELE\x02\x00\x11\x27" + bytes(13), id="just-over-100"),
        pytest.param(b"OTOTELE\x02\x00\xff\xff" + bytes(13), id="max-raw"),
    ],
)
def test_parse_telemetry_invalid(
    payload: bytes, caplog: pytest.LogCaptureFixture
) -> None:
    """Invalid or out-of-range telemetry returns None and logs its hex."""
    with caplog.at_level(logging.DEBUG):
        assert parse_telemetry(payload) is None
    assert payload.hex() in caplog.text


@pytest.mark.parametrize(
    ("name", "level"),
    [
        pytest.param("level: 80 % vertica", 80.0, id="cut-short"),
        pytest.param("level: 32.6 % vertical", 32.6, id="decimal"),
        pytest.param("level: 5 % vertical", 5.0, id="one-digit"),
        pytest.param("level: 100 % verti", 100.0, id="full"),
        pytest.param("level: 0 % vertical", 0.0, id="empty"),
    ],
)
def test_parse_name_level(name: str, level: float) -> None:
    """The level is read from the rotating local name."""
    assert parse_name_level(name) == OtodataTelemetry(level=level)


@pytest.mark.parametrize(
    "name",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("Bell         R1|-66", id="other-name"),
        pytest.param("unit sleeping", id="sleeping"),
        pytest.param("trbl:ACC (32.6)", id="trouble"),
        pytest.param("TM6030 20479133", id="model-serial"),
        pytest.param("CA:A0:26:0B:8C:9B", id="address"),
        pytest.param("level: 101 % vertical", id="over-100"),
    ],
)
def test_parse_name_level_none(name: str | None) -> None:
    """Names without a valid level return None."""
    assert parse_name_level(name) is None
