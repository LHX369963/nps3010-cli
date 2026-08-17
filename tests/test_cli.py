import json

from nps3010_cli import cli
from nps3010_cli.protocol import State


class FakeContext:
    def __init__(self, port, timeout, retries):
        self.port = port

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def state(self):
        return State(False, 5.0, 1.0, 0.0, 0.0, 0.0, "set", 0)


def test_state_json(monkeypatch, capsys):
    monkeypatch.setattr(cli, "SerialTransport", FakeContext)
    assert cli.main(["--port", "/dev/test", "state"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["slot"] == 1
    assert result["port"] == "/dev/test"
    assert result["set_voltage_v"] == 5


def test_multiple_units_require_explicit_selection(monkeypatch, capsys):
    monkeypatch.setattr(cli, "SerialTransport", FakeContext)
    assert cli.main(["--port", "/dev/a", "--port", "/dev/b", "state"]) == 4
    assert "multiple NPS3010" in capsys.readouterr().err


def test_second_device_selection(monkeypatch, capsys):
    monkeypatch.setattr(cli, "SerialTransport", FakeContext)
    assert (
        cli.main(
            [
                "--port",
                "/dev/a",
                "--port",
                "/dev/b",
                "--device",
                "2",
                "state",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["port"] == "/dev/b"


def test_readback_aggregates_internally(monkeypatch, capsys):
    monkeypatch.setattr(cli, "SerialTransport", FakeContext)
    assert cli.main([
        "--port", "/dev/test", "readback", "--samples", "3",
        "--min-interval", "0", "--max-interval", "0",
    ]) == 0
    assert capsys.readouterr().out == "0.0 V 0.0 A vspread=0 aspread=0\n"
