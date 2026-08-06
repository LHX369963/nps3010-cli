import pytest

from psu_cli.errors import ProtocolError
from psu_cli.protocol import parse_adc, parse_state


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
