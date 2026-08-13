import struct

import pytest

from psu_cli.errors import ProtocolError
from psu_cli.protocol import crc16_ccitt, parse_adc, parse_state, parse_telemetry


def test_parse_state():
    state = parse_state(
        "STATE output=1 setU=5000 mV setI=1000 mA actualU=4998 mV "
        "actualI=123 mA actualP=615 mW view=live digit=2"
    )
    assert state.output is True
    assert state.set_voltage_v == 5
    assert state.set_current_a == 1
    assert state.voltage_v == 4.998
    assert state.current_a == 0.123
    assert state.power_w == 0.615
    assert state.view == "live"
    assert state.selected_digit == 2


def test_parse_adc():
    reading = parse_adc(
        "ADC voltage_feedback=2048 (1650 mV), current_feedback=100 (81 mV)"
    )
    assert reading.voltage_raw == 2048
    assert reading.voltage_pin_v == 1.65
    assert reading.current_raw == 100
    assert reading.current_pin_v == 0.081


def test_parse_extended_state():
    state = parse_state(
        "STATE output=0 setU=4100 mV setI=100 mA actualU=0 mV "
        "actualI=0 mA actualP=0 mW view=set vdigit=0 idigit=1 "
        "cc=0 settling=1 fault=NONE"
    )
    assert state.output is False
    assert state.selected_digit is None
    assert state.selected_voltage_digit == 0
    assert state.selected_current_digit == 1
    assert state.constant_current is False
    assert state.settling is True
    assert state.fault == "NONE"


def test_reject_bad_state():
    with pytest.raises(ProtocolError):
        parse_state("OK STATE")


def test_parse_binary_telemetry():
    frame = bytearray(b"\xA5\x5A")
    frame += struct.pack("<BBHIHHBB", 1, 0b111, 65534, 123456, 15029, 1122, 0, 0)
    frame += struct.pack("<H", crc16_ccitt(frame))
    item = parse_telemetry(bytes(frame))
    assert item.sequence == 65534
    assert item.device_time_ms == 123456
    assert item.voltage_v == 15.029
    assert item.current_a == 1.122
    assert item.power_w == 16.862538
    assert item.output and item.constant_current and item.settling
    assert item.fault == "NONE"


def test_reject_bad_telemetry_crc():
    frame = bytearray(18)
    frame[:4] = b"\xA5\x5A\x01\x00"
    with pytest.raises(ProtocolError, match="CRC"):
        parse_telemetry(bytes(frame))
