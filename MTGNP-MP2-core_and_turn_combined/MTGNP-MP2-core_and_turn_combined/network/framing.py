import struct

from shared.errors import ConnectionError

MAX_MESSAGE_SIZE = 65535

def recv_exact(socket, num_bytes):
    """
    Receive exactly num_bytes from the socket.

    Raises:
        ConnectionError if the socket closes unexpectedly.
    """
    data = bytearray()

    while len(data) < num_bytes:
        packet = socket.recv(num_bytes - len(data))

        if not packet:
            raise ConnectionError("Socket closed while receiving data.")

        data.extend(packet)

    return bytes(data)

def send_frame(socket, payload):
    """
    Sends a payload with a 4-byte big-endian length prefix.

    Paramters
    ---------
    socket : socket.socket
        Connected socket.
    payload : bytes
        UTF-8 encoded JSON bytes.
    """
    if not isinstance(payload, bytes):
        raise TypeError("Payload must be bytes.")

    length = len(payload)

    if length > MAX_MESSAGE_SIZE:
        raise ConnectionError("Message exceeds MTGNP maximum size.")
    
    header = struct.pack(">I", length)
    socket.sendall(header + payload)

def receive_frame(socket):
    """
    Receives one complete framed message.

    Returns
    -------
    bytes
        The payload without the length prefix.
    """

    header = recv_exact(socket, 4)
    (length,) = struct.unpack(">I", header)

    if length > MAX_MESSAGE_SIZE:
        raise ConnectionError("Message exceeds MTGNP maximum size.")

    payload = recv_exact(socket, length)

    return payload
