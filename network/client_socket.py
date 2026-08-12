import socket

from shared.errors import ConnectionError

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4444

class GameClientSocket:
    """
    Handles TCP connection to an MTGNP server.
    """

    def __init__(self, host = DEFAULT_HOST, port = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.socket = None

    def connect(self):
        """
        Connects to the game server.
        """

        self.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        try:
            self.socket.connect((self.host, self.port))
            print(f"Connected to server {self.host}:{self.port}")
        except OSError as ex:
            self.socket.close()
            self.socket = None

            raise ConnectionError(f"Unable to connect to {self.host}:{self.port}") from ex

    def close(self):
        """
        Closes the client connection.
        """

        if self.socket:
            self.socket.close()
            self.socket = None
