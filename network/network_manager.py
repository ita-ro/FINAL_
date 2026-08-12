from network.protocol import send_message


class NetworkManager:
    """
    Tracks player sockets, sequence numbers, and outbound messaging.
    """

    def __init__(self):
        self._socket_to_player = {}
        self._player_to_socket = {}
        self._server_seq_num = 0

    def register_player(self, player_id: str, client_socket) -> None:
        if player_id in self._player_to_socket:
            raise ValueError(f"Player ID already registered: {player_id}")
        
        self._socket_to_player[client_socket] = player_id
        self._player_to_socket[player_id] = client_socket

    def unregister_player(self, client_socket):
        """
        Removes a disconnected client's socket and player mapping
        """
        player_id = self._socket_to_player.pop(client_socket, None)

        if player_id is not None:
            self._player_to_socket.pop(player_id, None)

        return player_id

    def get_player_id(self, client_socket):
        return self._socket_to_player.get(client_socket)

    def get_socket_for_player(self, player_id: str):
        return self._player_to_socket.get(player_id)

    def send_message(self, client_socket, message: dict) -> None:
        send_message(client_socket, message)

    def send_to_player(self, player_id: str, message: dict) -> None:
        client_socket = self.get_socket_for_player(player_id)

        if client_socket is not None:
            self.send_message(client_socket, message)

    def broadcast_to_all(self, message: dict) -> None:
        for client_socket in list(self._player_to_socket.values()):
            self.send_message(client_socket, message)

    def next_server_seq_num(self):
        """
        Returns the next server-generated sequence number
        """

        self._server_seq_num += 1
        return self._server_seq_num
    
