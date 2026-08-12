import argparse

from network.client_socket import GameClientSocket
from network.protocol import (
    receive_message,
    send_message,
    set_verbose
)
from network.heartbeat import HeartbeatManager
from shared.errors import ConnectionError, ProtocolError


class GameClient:
    """
    Main client-side networking controller.
    """

    def __init__(self, host = "127.0.0.1", port=4444):
        self.socket = GameClientSocket(host, port)
        self.running = False
        self._seq_num = 0
        
        # Cached token to echo for priority actions
        self.current_priority_token = 0 
        # Track newest token for CONCEDE
        self.absolute_latest_seq = 0 
        
        self.heartbeat = HeartbeatManager(self)

    def start(self):
        """
        Connects to the server and starts receiving messages.
        """

        self.socket.connect()
        self.running = True
        self.heartbeat.start()

        print("Client started.")

        while self.running:
            try:
                message = receive_message(self.socket.socket)
                self.handle_message(message)

            except ConnectionError as ex:
                print(f"Connection lost: {ex}")
                self.running = False

            except ProtocolError as ex:
                print(f"Protocol error: {ex}")

            except OSError as ex:
                print(f"Socket error: {ex}")
                self.running = False

        self.stop()

    def handle_message(self, message):
        """Handles an incoming server PDU and caches seq_nums for echoing."""
        msg_type = message.get("type")
        seq_num = message.get("seq_num", 0)

        # Track newest token of any type for CONCEDE
        if seq_num > self.absolute_latest_seq:
            self.absolute_latest_seq = seq_num
        
        if msg_type == "PONG":
            self.heartbeat.handle_pong(message)
            return

        # Cache seq_num for server PDUs per section 5.4
        if msg_type in ["PRIORITY_GRANT", "GAME_STATE_UPDATE", "PHASE_TRANSITION"]:
            self.current_priority_token = seq_num

        # Basic text-based UI rendering
        if msg_type == "GAME_STATE_UPDATE":
            self._render_state(message.get("state", {}))
        elif msg_type == "ERROR":
            print(f"\n[SERVER ERROR] {message.get('code')}: {message.get('message')}")
        else:
            print(f"\n[SERVER] -> {msg_type} (seq: {seq_num})")

    def _render_state(self, state):
        """Basic text-based UI rendering of the visible game state."""
        print("\n" + "="*50)
        print(f"--- GAME STATE UPDATE | Phase: {state.get('phase')} ---")
        if state.get("phase") == "LOBBY":
            print(f"Waiting for players... ({state.get('players_ready', 0)}/2 ready)")
        else:
            print(f"Turn: {state.get('turn')} | Active Player: {state.get('active_player')}")
            print("\nLife Totals:")
            for pid, life in state.get("life_totals", {}).items():
                print(f"  {pid}: {life} life")
            print(f"\nYour Hand ({len(state.get('hand', {}).values())} cards):")
            for pid, hand in state.get("hand", {}).items():
                print(f"  {hand}")
        print("="*50 + "\n")

    def send_action(self, action_type, **kwargs):
        """Helper method to send game actions using the echoed priority token."""
        message = {
            "type": action_type,
            "seq_num": self.current_priority_token
        }
        message.update(kwargs)
        self.send_message(message)

    def send_concede(self):
        """Sends a concede PDU using the latest token."""
        self.send_message({"type": "CONCEDE", "seq_num": self.absolute_latest_seq})

    def send_player_ready(self, player_id, deck_list):
        """Sends PLAYER_READY using the independent client counter."""
        self.send_message({
            "type": "PLAYER_READY",
            "seq_num": self.next_seq_num(),
            "player_id": player_id,
            "deck_list": deck_list
        })

    def send_message(self, message):
        """
        Sends a protocol message to the server.
        """

        send_message(
            self.socket.socket,
            message
        )

    def stop(self):
        """
        Closes the client connection.
        """

        self.running = False
        self.heartbeat.stop()
        self.socket.close()

    def next_seq_num(self):
        """
        Returns the next client-generated sequence number
        """

        self._seq_num += 1
        return self._seq_num


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "MTGNP Player Client"
    )

    parser.add_argument(
        "--verbose",
        action = "store_true",
        help = "Enable verbose PDU logging."
    )

    args = parser.parse_args()

    set_verbose(args.verbose, "CLIENT")

    client = GameClient()
    client.start()