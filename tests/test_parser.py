"""Tests for the Otodata payload parser, using real captured payloads."""

import logging

import pytest

from custom_components.otodata_ble.parser import (
    OtodataInfo,
    OtodataTelemetry,
    PacketType,
    get_packet_type,
    parse_info,
    parse_telemetry,
)

# TM6030, serial 20479133
INFO_TM6030 = "4f544f333238319d7c38010d1210036404021a8e170004"
# Second-hand sample from another monitor: TM5040, serial 29122704
INFO_TM5040 = "4f544f333238319060bc011018210384060304b0130205"

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
    ("payload", "serial", "model"),
    [
        (INFO_TM6030, 20479133, "TM6030"),
        (INFO_TM5040, 29122704, "TM5040"),
    ],
)
def test_parse_info(payload: str, serial: int, model: str) -> None:
    """Info packets decode to the right serial number and model."""
    info = parse_info(bytes.fromhex(payload))
    assert info == OtodataInfo(serial=serial, model_number=int(model[2:]))
    assert info.model == model


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(bytes.fromhex(INFO_TM6030)[:20], id="truncated"),
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
