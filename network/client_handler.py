import threading

from network.protocol import receive_message
from shared.errors import ConnectionError, ProtocolError


class ClientHandler:
    """
    Handles communication with a single connected client.
    """

    def __init__(self, client_socket, dispatcher, on_disconnect = None, on_protocol_error = None):
        self.client_socket = client_socket
        self.dispatcher = dispatcher
        self.on_disconnect = on_disconnect
        self.on_protocol_error = on_protocol_error
        self.running = False
        self.thread = None

    def start(self):
        """
        Starts the client handler in a separate thread.
        """

        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(
            target=self.run,
            daemon=True
        )

        self.thread.start()

    def run(self):
        """
        Continuously receives and dispatches PDUs from the client.
        """

        while self.running:
            try:
                message = receive_message(self.client_socket)

                self.dispatcher.dispatch(
                    message,
                    self.client_socket
                )

            except ConnectionError as ex:
                print(f"Client disconnected: {ex}")
                self.running = False

                if self.on_disconnect:
                    self.on_disconnect(self.client_socket)

            except ProtocolError as ex:
                print(f"Protocol error: {ex}")

                if self.on_protocol_error:
                    self.on_protocol_error(
                        self.client_socket,
                        str(ex)
                    )

            except OSError as ex:
                print(f"Socket error: {ex}")
                self.running = False

                if self.on_disconnect:
                    self.on_disconnect(self.client_socket)

    def stop(self):
        """
        Stops the client handler.
        """

        self.running = False

        try:
            self.client_socket.shutdown(2)
        except OSError:
            pass