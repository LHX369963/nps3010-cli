from dataclasses import dataclass

import pytest

from psu_cli.errors import ProtocolError, TransportError
from psu_cli.transport import PortInfo, SerialTransport, select_ports


def test_encode():
    assert SerialTransport.encode(" STATE ") == b"STATE\n"
    with pytest.raises(ProtocolError):
        SerialTransport.encode("ON\nOFF")


def test_select_two_explicit_ports():
    assert select_ports(["/dev/a", "/dev/b"], "all") == [
        (1, "/dev/a"),
        (2, "/dev/b"),
    ]
    assert select_ports(["/dev/a", "/dev/b"], "2") == [(2, "/dev/b")]


def test_reject_more_than_two():
    with pytest.raises(TransportError, match="at most two"):
        select_ports(["a", "b", "c"], "all")


def test_missing_slot():
    with pytest.raises(TransportError, match="not connected"):
        select_ports(["a"], "2")
