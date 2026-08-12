import json

from network.framing import send_frame, receive_frame
from shared.errors import ProtocolError

_VERBOSE = False
_ROLE = "NETWORK"

def set_verbose(enabled, role = "NETWORK"):
    """
    Enables or disables verbose PDU logging.
    
    Parameters
    ----------
    enabled : bool
        Whether verbose logging is enabled.
    role : str
        Label identifying the program printing the PDU.
    """
    global _VERBOSE, _ROLE

    _VERBOSE = enabled
    _ROLE = role

def _log_pdu(direction, message):
    """
    Prints a PDU when verbose mode is enabled.
    """

    if not _VERBOSE:
        return

    print()
    print("=" * 60)
    print(f"[{_ROLE}] {direction} PDU")
    print("=" * 60)
    print(json.dumps(message, indent = 4))
    print("=" * 60)

def send_message(socket, message):
    """
    Sends a protocol message.

    Parameters
    ----------
    socket : socket.socket
        Connected socket.

    message : dict
        MTGNP message dictionary.
    """

    if not isinstance(message, dict):
        raise ProtocolError("Message must be a dictionary.")

    if "type" not in message:
        raise ProtocolError("Missing required field: type")

    if "seq_num" not in message:
        raise ProtocolError("Missing required field: seq_num")

    _log_pdu(">>> SENT", message)

    json_bytes = json.dumps(message).encode("utf-8")
    send_frame(socket, json_bytes)

def receive_message(socket):
    """
    Receives one protocol message.

    Returns
    -------
    dict
        Parsed JSON message.
    """

    payload = receive_frame(socket)

    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as ex:
        raise ProtocolError("Received message encoding or JSON format.") from ex

    if not isinstance(message, dict):
        raise ProtocolError("Received message must be a dictionary.")

    if "type" not in message:
        raise ProtocolError("Received message missing required field: type")

    if "seq_num" not in message:
        raise ProtocolError("Received message missing requied field: seq_num")

    _log_pdu("<<< RECEIVED", message)
    
    return message

