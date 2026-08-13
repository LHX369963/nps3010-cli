"""Parser for the line-oriented firmware protocol."""

from __future__ import annotations

import re
import binascii
import struct
from dataclasses import asdict, dataclass

from .errors import ProtocolError


STATE_RE = re.compile(
    r"^STATE output=(?P<output>[01]) "
    r"setU=(?P<set_u>\d+) mV setI=(?P<set_i>\d+) mA "
    r"actualU=(?P<actual_u>\d+) mV actualI=(?P<actual_i>\d+) mA "
    r"actualP=(?P<actual_p>\d+) mW view=(?P<view>set|live) "
    r"(?:digit=(?P<digit>\d+)|"
    r"vdigit=(?P<vdigit>\d+) idigit=(?P<idigit>\d+) "
    r"cc=(?P<cc>[01]) settling=(?P<settling>[01]) fault=(?P<fault>\S+))$"
)

ADC_RE = re.compile(
    r"^ADC voltage_feedback=(?P<voltage_raw>\d+) "
    r"\((?P<voltage_mv>\d+) mV\), current_feedback=(?P<current_raw>\d+) "
    r"\((?P<current_mv>\d+) mV\)$"
)

TELEMETRY_SOF = b"\xA5\x5A"
TELEMETRY_FRAME_SIZE = 18


@dataclass(frozen=True)
class State:
    output: bool
    set_voltage_v: float
    set_current_a: float
    voltage_v: float
    current_a: float
    power_w: float
    view: str
    selected_digit: int | None
    selected_voltage_digit: int | None = None
    selected_current_digit: int | None = None
    constant_current: bool = False
    settling: bool = False
    fault: str = "NONE"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ADCReading:
    voltage_raw: int
    voltage_pin_v: float
    current_raw: int
    current_pin_v: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Telemetry:
    version: int
    sequence: int
    device_time_ms: int
    voltage_v: float
    current_a: float
    power_w: float
    output: bool
    constant_current: bool
    settling: bool
    fault: str

    def to_dict(self) -> dict:
        return asdict(self)


def crc16_ccitt(data: bytes) -> int:
    return binascii.crc_hqx(data, 0xFFFF)


def parse_telemetry(frame: bytes) -> Telemetry:
    if len(frame) != TELEMETRY_FRAME_SIZE or frame[:2] != TELEMETRY_SOF:
        raise ProtocolError("invalid telemetry frame")
    expected, = struct.unpack_from("<H", frame, 16)
    if crc16_ccitt(frame[:16]) != expected:
        raise ProtocolError("telemetry CRC mismatch")
    version, flags, sequence, device_time_ms, voltage_mv, current_ma, fault = (
        struct.unpack_from("<BBHIHHB", frame, 2)
    )
    if version != 1:
        raise ProtocolError(f"unsupported telemetry version {version}")
    fault_names = {0: "NONE", 1: "VOLTAGE", 2: "OVERCURRENT"}
    return Telemetry(
        version=version,
        sequence=sequence,
        device_time_ms=device_time_ms,
        voltage_v=voltage_mv / 1000,
        current_a=current_ma / 1000,
        power_w=voltage_mv * current_ma / 1_000_000,
        output=bool(flags & 1),
        constant_current=bool(flags & 2),
        settling=bool(flags & 4),
        fault=fault_names.get(fault, f"UNKNOWN_{fault}"),
    )


def parse_state(line: str) -> State:
    match = STATE_RE.fullmatch(line.strip())
    if not match:
        raise ProtocolError(f"invalid STATE response: {line!r}")
    values = match.groupdict()
    return State(
        output=values["output"] == "1",
        set_voltage_v=int(values["set_u"]) / 1000,
        set_current_a=int(values["set_i"]) / 1000,
        voltage_v=int(values["actual_u"]) / 1000,
        current_a=int(values["actual_i"]) / 1000,
        power_w=int(values["actual_p"]) / 1000,
        view=values["view"],
        selected_digit=int(values["digit"]) if values["digit"] is not None else None,
        selected_voltage_digit=(
            int(values["vdigit"]) if values["vdigit"] is not None else None
        ),
        selected_current_digit=(
            int(values["idigit"]) if values["idigit"] is not None else None
        ),
        constant_current=values["cc"] == "1",
        settling=values["settling"] == "1",
        fault=values["fault"] or "NONE",
    )


def parse_adc(line: str) -> ADCReading:
    match = ADC_RE.fullmatch(line.strip())
    if not match:
        raise ProtocolError(f"invalid READ response: {line!r}")
    values = {key: int(value) for key, value in match.groupdict().items()}
    return ADCReading(
        voltage_raw=values["voltage_raw"],
        voltage_pin_v=values["voltage_mv"] / 1000,
        current_raw=values["current_raw"],
        current_pin_v=values["current_mv"] / 1000,
    )
