class MTGNPError(Exception):
    """
    Base exception for MTGNP-related errors.
    """
    pass

class ProtocolError(MTGNPError):
    """
    Raised when a message violates the MTGNP protocol.
    """
    pass

class ConnectionError(MTGNPError):
    """
    Raised when a connection problem occurs.
    """
    pass

