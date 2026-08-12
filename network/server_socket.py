import socket
import threading

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 4444
MAX_CLIENTS = 2

class GameServerSocket:
    """
    Handles TCP connections from MTGNP clients.
    """

    def __init__(self, host = DEFAULT_HOST, port = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []

    def start(self):
        """
        Creates and starts the TCP listening socket.
        """

        self.server_socket = socket.socket(
            socket.AF_INET, 
            socket.SOCK_STREAM
        )

        # Allows quick restart after shutdown
        self.server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(MAX_CLIENTS)
        print(f"Server listening on {self.host}:{self.port}")

    def accept_clients(self):
        """
        Accept exactly two clients, then launch a thread to reject any others.
        """
        while len(self.clients) < MAX_CLIENTS:
            client_socket, address = self.server_socket.accept()
            print(f"Client connected: {address}")
            self.clients.append(client_socket)

        reject_thread = threading.Thread(target=self._reject_excess_clients, daemon=True)
        reject_thread.start()

        return self.clients

    def _reject_excess_clients(self):
        """
        Continuously listens for extra connections and immediately closes them.
        """
        while True:
            try:
                client_socket, _ = self.server_socket.accept()
                print("Refused excess connection.")
                client_socket.close()
            except OSError:
                break

    def close(self):
        """
        Closes all sockets.
        """

        for client in self.clients:
            client.close()

        self.clients.clear()

        if self.server_socket:
            self.server_socket.close()
