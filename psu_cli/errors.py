class PSUError(Exception):
    """Base error shown without a traceback by the CLI."""


class TransportError(PSUError):
    """Serial transport failed."""


class ProtocolError(PSUError):
    """The board response did not match the firmware protocol."""
