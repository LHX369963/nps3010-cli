"""CH340 discovery and resilient transport for the isolated UART."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Callable

import serial
from serial.tools import list_ports

from .errors import ProtocolError, TransportError
from .protocol import (
    TELEMETRY_FRAME_SIZE,
    TELEMETRY_SOF,
    State,
    Telemetry,
    parse_state,
    parse_telemetry,
)


VID = 0x1A86
PID = 0x7523
MAX_DEVICES = 2


@dataclass(frozen=True)
class PortInfo:
    port: str
    location: str | None
    usb_serial: str | None
    manufacturer: str | None
    product: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def serial_ports() -> list[PortInfo]:
    ports = [
        PortInfo(
            port=item.device,
            location=item.location,
            usb_serial=item.serial_number,
            manufacturer=item.manufacturer,
            product=item.product,
        )
        for item in list_ports.comports()
        if item.vid == VID and item.pid == PID
    ]
    return sorted(ports, key=lambda item: (item.location or "", item.port))


class SerialTransport:
    def __init__(
        self,
        port: str,
        timeout: float = 1.0,
        retries: int = 10,
        quiet: float = 0.12,
    ) -> None:
        if timeout <= 0 or quiet < 0 or retries < 0:
            raise TransportError("timeout must be positive; quiet/retries cannot be negative")
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.quiet = quiet
        self._serial: serial.Serial | None = None

    def open(self) -> "SerialTransport":
        try:
            self._serial = serial.Serial(
                self.port,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=min(0.1, self.timeout),
                write_timeout=self.timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
                exclusive=True,
            )
            self._serial.reset_input_buffer()
        except (OSError, serial.SerialException) as exc:
            self.close()
            raise TransportError(f"cannot open {self.port}: {exc}") from exc
        return self

    @property
    def serial(self) -> serial.Serial:
        if self._serial is None:
            raise TransportError("serial session is not open")
        return self._serial

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None

    @staticmethod
    def encode(command: str) -> bytes:
        command = command.strip()
        if not command or "\r" in command or "\n" in command:
            raise ProtocolError("command must be one non-empty ASCII line")
        try:
            return (command + "\n").encode("ascii")
        except UnicodeEncodeError as exc:
            raise ProtocolError("commands must be ASCII") from exc

    def command(self, command: str) -> list[str]:
        try:
            self.serial.reset_input_buffer()
            # Automatic telemetry is enabled at boot.  Pause it for the brief
            # request/response transaction so legacy ASCII parsing remains
            # deterministic, then restore streaming before returning.
            self.serial.write(self.encode("TELEM OFF"))
            self.serial.flush()
            time.sleep(0.08)
            self.serial.reset_input_buffer()
            self.serial.write(self.encode(command))
            self.serial.flush()
            lines: list[str] = []
            deadline = time.monotonic() + self.timeout
            last_data = time.monotonic()
            ascii_line = bytearray()
            while time.monotonic() < deadline:
                raw = self.serial.read(1)
                if raw:
                    last_data = time.monotonic()
                    if raw == TELEMETRY_SOF[:1]:
                        second = self.serial.read(1)
                        if second == TELEMETRY_SOF[1:]:
                            rest = self.serial.read(TELEMETRY_FRAME_SIZE - 2)
                            if len(rest) == TELEMETRY_FRAME_SIZE - 2:
                                try:
                                    parse_telemetry(raw + second + rest)
                                    continue
                                except ProtocolError:
                                    ascii_line.extend(raw + second + rest)
                            else:
                                ascii_line.extend(raw + second + rest)
                        else:
                            ascii_line.extend(raw + second)
                    elif raw in (b"\r", b"\n"):
                        text = ascii_line.decode("ascii", "replace").strip()
                        ascii_line.clear()
                        if text:
                            lines.append(text)
                            # All routine CLI responses have a known first line;
                            # avoid the legacy 120 ms quiet wait where possible.
                            if command == "STATE" and text.startswith("STATE "):
                                break
                    else:
                        ascii_line.extend(raw)
                elif lines and time.monotonic() - last_data >= self.quiet:
                    break
            if command != "TELEM OFF":
                self.serial.write(self.encode("TELEM ON"))
                self.serial.flush()
            return lines
        except (OSError, serial.SerialException, serial.SerialTimeoutException) as exc:
            raise TransportError(f"serial I/O failed on {self.port}: {exc}") from exc

    def command_until(self, command: str, prefix: str) -> list[str]:
        last: list[str] = []
        for attempt in range(self.retries + 1):
            last = self.command(command)
            if any(line.startswith(prefix) for line in last):
                return last
            if attempt < self.retries:
                time.sleep(0.1)
        raise TransportError(
            f"{self.port} did not acknowledge {command!r} after "
            f"{self.retries + 1} attempts (last response: {last!r})"
        )

    def state(self) -> State:
        lines = self.command_until("STATE", "STATE ")
        line = next(line for line in lines if line.startswith("STATE "))
        return parse_state(line)

    def telemetry(self, duration: float = 0, count: int = 0):
        started = time.monotonic()
        matched = 0
        while (not duration or time.monotonic() - started < duration) and (
            not count or matched < count
        ):
            byte = self.serial.read(1)
            if byte != TELEMETRY_SOF[:1]:
                continue
            if self.serial.read(1) != TELEMETRY_SOF[1:]:
                continue
            rest = self.serial.read(TELEMETRY_FRAME_SIZE - 2)
            if len(rest) != TELEMETRY_FRAME_SIZE - 2:
                continue
            try:
                record = parse_telemetry(TELEMETRY_SOF + rest)
            except ProtocolError:
                continue
            matched += 1
            yield record

    def __enter__(self) -> "SerialTransport":
        return self.open()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


TransportFactory = Callable[[str, float, int], SerialTransport]


def probe(port: str, timeout: float, retries: int) -> State:
    with SerialTransport(port, timeout, retries) as transport:
        return transport.state()


def discover(timeout: float, retries: int) -> list[dict]:
    found = []
    for slot, metadata in enumerate(serial_ports(), 1):
        item = {"slot": slot, **metadata.to_dict()}
        try:
            item["state"] = probe(metadata.port, timeout, retries).to_dict()
            item["compatible"] = True
        except (TransportError, ProtocolError) as exc:
            item["compatible"] = False
            item["error"] = str(exc)
        found.append(item)
    return found


def select_ports(explicit: list[str] | None, device: str) -> list[tuple[int, str]]:
    if explicit:
        paths = list(dict.fromkeys(explicit))
    else:
        paths = [item.port for item in serial_ports()]
    if len(paths) > MAX_DEVICES:
        raise TransportError(
            f"{len(paths)} CH340/explicit ports found; this controller supports at most two"
        )
    if not paths:
        raise TransportError("no CH340 serial port found; connect a PSU or use --port")
    indexed = list(enumerate(paths, 1))
    if device == "all":
        return indexed
    slot = int(device)
    if slot > len(indexed):
        raise TransportError(f"PSU slot {slot} is not connected")
    return [indexed[slot - 1]]
