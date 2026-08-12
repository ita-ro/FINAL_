import threading
import argparse

from models.game_state import GameState
from shared.catalog import CardDatabase
from network.server_socket import GameServerSocket
from network.dispatcher import Dispatcher
from network.protocol import set_verbose
from network.heartbeat import handle_ping
from network.network_manager import NetworkManager
from network.client_handler import ClientHandler
from handlers.lobby import handle_player_ready, handle_mulligan_choice
from handlers.rules import handle_concede, check_state_based_actions
from priority_stack.stack_manager import StackManager
from turn_engine.trigger_manager import TriggerManager
from priority_stack.priority_manager import PriorityManager
from turn_engine.turn_manager import TurnManager

PRIORITY_PDU_TYPES = {
    "PRIORITY_PASS",
    "CAST_SPELL",
    "ACTIVATE_ABILITY",
    "PLAY_LAND",
    "TRIGGER_ORDER_RESPONSE",
    "TRIGGER_CHOICE_RESPONSE",
}


class GameServer:
    def __init__(self):
        CardDatabase.load_catalog()
        self.game_state = GameState()
        self.network_manager = NetworkManager()
        self.server_socket = GameServerSocket()
        self.dispatcher = Dispatcher(self.network_manager)
        self.clients = []

        self.stack_manager = StackManager()
        self.trigger_manager = TriggerManager(self.stack_manager)
        self.turn_manager = TurnManager(self.game_state, self.network_manager)
        self.priority_manager = PriorityManager(
            self.stack_manager,
            self.trigger_manager,
            self.turn_manager.priority_window_closes,
        )
        self.turn_manager.set_priority_manager(self.priority_manager)

        self.dispatcher.register_handler("PLAYER_READY", self._handle_player_ready)
        self.dispatcher.register_handler("MULLIGAN_CHOICE", self._handle_mulligan_choice)
        self.dispatcher.register_handler("CONCEDE", self._handle_concede)
        self.dispatcher.register_handler("PING", handle_ping)
        for pdu_type in PRIORITY_PDU_TYPES:
            self.dispatcher.register_handler(pdu_type, self._handle_priority_pdu)

    def start(self):
        self.server_socket.start()
        self.clients = self.server_socket.accept_clients()
        print("Both players connected.")
        self.start_client_handlers()

        for handler in self.handlers:
            handler.thread.join()

    def _handle_player_ready(self, pdu, client):
        player_id = str(pdu.get("player_id", "")).strip()
        if player_id and player_id not in self.game_state.players:
            self.network_manager.register_player(player_id, client)
        handle_player_ready(pdu, client, self.game_state, self.network_manager)

    def _handle_mulligan_choice(self, pdu, client):
        handle_mulligan_choice(
            pdu,
            client,
            self.game_state,
            self.network_manager,
            turn_manager=self.turn_manager,
        )

    def _handle_concede(self, pdu, client):
        handle_concede(pdu, client, self.game_state, self.network_manager)

    def _handle_priority_pdu(self, pdu, client):
        player_id = self.network_manager.get_player_id(client)
        if player_id is None:
            return
        pdus = self.priority_manager.handle_client_pdu(self.game_state, player_id, pdu)
        for outgoing in pdus:
            target = self.network_manager.get_socket_for_player(outgoing.get("player_id", player_id))
            if target:
                self.network_manager.send_message(target, outgoing)
        check_state_based_actions(self.game_state, self.network_manager)

    def _handle_disconnect(self, client):
        print("Handling client disconnect.")

        player_id = self.network_manager.unregister_player(client)

        if player_id:
            print(f"Player disconnected: {player_id}")

        if client in self.clients:
            self.clients.remove(client)

        client.close()

    def start_client_handlers(self):
        """
        Creates and starts a ClientHandler for each connected client.
        """
        self.handlers = []

        for client in self.clients:
            handler = ClientHandler(
                client,
                self.dispatcher,
                self._handle_disconnect,
                self._handle_protocol_error
            )

            self.handlers.append(handler)
            handler.start()

    def _handle_protocol_error(self, client, message):
        self.network_manager.send_message(
            client,
            {
                "type": "ERROR",
                "seq_num": self.network_manager.next_server_seq_num(),
                "code": "INVALID_JSON",
                "message": message
            }
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "MTGNP Game Server"
    )

    parser.add_argument(
        "--verbose",
        action = "store_true",
        help = "Enable verbose PDU logging."
    )

    args = parser.parse_args()

    set_verbose(args.verbose, "SERVER")

    server = GameServer()
    server.start()
