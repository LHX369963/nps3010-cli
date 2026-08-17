"""Typed operations on one NPS3010."""

from __future__ import annotations

from .errors import ProtocolError
from .protocol import ADCReading, State, parse_adc
from .transport import SerialTransport


class NPS3010:
    def __init__(self, transport: SerialTransport) -> None:
        self.transport = transport

    def state(self) -> State:
        return self.transport.state()

    def read_adc(self) -> ADCReading:
        lines = self.transport.command_until("READ", "ADC ")
        return parse_adc(next(line for line in lines if line.startswith("ADC ")))

    def set_targets(
        self, voltage_v: float | None = None, current_a: float | None = None
    ) -> State:
        if voltage_v is None and current_a is None:
            raise ProtocolError("set requires --voltage and/or --current")
        if voltage_v is not None:
            if not 0 <= voltage_v <= 30:
                raise ProtocolError("voltage must be between 0 and 30 V")
            self.transport.command_until(f"VSET {round(voltage_v * 1000)}", "OK VSET")
        if current_a is not None:
            if not 0 <= current_a <= 10:
                raise ProtocolError("current must be between 0 and 10 A")
            self.transport.command_until(f"ISET {round(current_a * 1000)}", "OK ISET")
        state = self.state()
        tolerance = 0.0005
        if voltage_v is not None and abs(state.set_voltage_v - voltage_v) > tolerance:
            raise ProtocolError(
                f"voltage readback mismatch: requested {voltage_v:g} V, "
                f"board reports {state.set_voltage_v:g} V"
            )
        if current_a is not None and abs(state.set_current_a - current_a) > tolerance:
            raise ProtocolError(
                f"current readback mismatch: requested {current_a:g} A, "
                f"board reports {state.set_current_a:g} A"
            )
        return state

    def output(self, enabled: bool) -> State:
        self.transport.command_until("ON" if enabled else "OFF", "OK ON" if enabled else "OK OFF")
        state = self.state()
        if state.output != enabled:
            raise ProtocolError("output state did not match the requested state")
        return state

    def zero(self) -> State:
        self.transport.command_until("ZERO", "OK ZERO")
        state = self.state()
        if state.output:
            raise ProtocolError("ZERO was acknowledged but output remains enabled")
        return state

    def view(self, mode: str) -> State:
        self.transport.command_until(f"VIEW {mode.upper()}", f"OK VIEW {mode.upper()}")
        state = self.state()
        if state.view != mode:
            raise ProtocolError("display mode did not match the requested mode")
        return state
