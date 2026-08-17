class NPS3010Error(Exception):
    """Base error shown without a traceback by the CLI."""


class TransportError(NPS3010Error):
    """Serial transport failed."""


class ProtocolError(NPS3010Error):
    """The board response did not match the firmware protocol."""
