from psu_cli.instrument import PSU


class FakeTransport:
    def __init__(self):
        self.commands = []
        self.voltage = 5.0
        self.current = 1.0
        self.enabled = False
        self.mode = "set"

    def command_until(self, command, prefix):
        self.commands.append(command)
        if command.startswith("VSET "):
            self.voltage = int(command.split()[1]) / 1000
        elif command.startswith("ISET "):
            self.current = int(command.split()[1]) / 1000
        elif command == "ON":
            self.enabled = True
        elif command in {"OFF", "ZERO"}:
            self.enabled = False
        elif command.startswith("VIEW "):
            self.mode = command.split()[1].lower()
        if command == "READ":
            return ["ADC voltage_feedback=12 (10 mV), current_feedback=34 (27 mV)"]
        return [prefix]

    def state(self):
        from psu_cli.protocol import State

        return State(
            self.enabled, self.voltage, self.current, 0.0, 0.0, 0.0, self.mode, 0
        )


def test_set_and_verify():
    transport = FakeTransport()
    state = PSU(transport).set_targets(12.345, 2.5)
    assert transport.commands == ["VSET 12345", "ISET 2500"]
    assert state.set_voltage_v == 12.345
    assert state.set_current_a == 2.5


def test_output_zero_and_view():
    transport = FakeTransport()
    psu = PSU(transport)
    assert psu.output(True).output is True
    assert psu.zero().output is False
    assert psu.view("live").view == "live"


def test_read_adc():
    reading = PSU(FakeTransport()).read_adc()
    assert reading.voltage_raw == 12
    assert reading.current_raw == 34
