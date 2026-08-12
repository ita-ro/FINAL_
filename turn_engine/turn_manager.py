"""Turn structure: phase progression and priority window lifecycle."""

from shared.pdu import make_pdu
from handlers.rules import check_state_based_actions


class TurnManager:
    PRIORITY_PHASES = {
        "UPKEEP",
        "DRAW",
        "PRECOMBAT_MAIN",
        "POSTCOMBAT_MAIN",
        "END_STEP",
    }

    COMBAT_PHASES = [
        "BEGIN_COMBAT",
        "DECLARE_ATTACKERS",
        "DECLARE_BLOCKERS",
        "COMBAT_DAMAGE",
        "END_OF_COMBAT",
    ]

    def __init__(self, game_state, network_manager):
        self.game_state = game_state
        self.network_manager = network_manager
        self.priority_manager = None

    def set_priority_manager(self, priority_manager) -> None:
        self.priority_manager = priority_manager

    def begin_game(self) -> None:
        """Start turn 1 after mulligans complete."""
        gs = self.game_state
        gs.turn = 1
        gs.phase = "UNTAP"
        self._run_untap_step()
        self._advance_from_untap()

    def priority_window_closes(self, state) -> list:
        """Called when both players pass with an empty stack."""
        if check_state_based_actions(state, self.network_manager):
            return []

        phase = state.phase
        if phase in self.PRIORITY_PHASES:
            return self._advance_from_priority_phase()
        return []

    def _broadcast_state(self) -> None:
        for pid in self.game_state.players:
            socket = self.network_manager.get_socket_for_player(pid)
            if socket:
                update = make_pdu(
                    self.game_state,
                    "GAME_STATE_UPDATE",
                    state = self.game_state.get_visible_state(pid)
                )
                self.network_manager.send_message(socket, update)

    def _broadcast_phase_transition(self, to_phase: str) -> None:
        transition_pdu = make_pdu(self.game_state, "PHASE_TRANSITION", to_phase=to_phase)
        for pid in self.game_state.players:
            socket = self.network_manager.get_socket_for_player(pid)
            if socket:
                self.network_manager.send_message(socket, transition_pdu)

    def _grant_active_priority(self) -> list:
        grant = self.priority_manager.grant_priority(self.game_state, self.game_state.active_player)
        self.network_manager.send_pdus([grant])
        return [grant]

    def _run_untap_step(self) -> None:
        for player in self.game_state.players.values():
            for permanent in player.battlefield:
                permanent.tapped = False
            player.reset_for_new_turn()

    def _advance_from_untap(self) -> list:
        self._broadcast_phase_transition("UPKEEP")
        self.game_state.phase = "UPKEEP"
        self._broadcast_state()
        return self._grant_active_priority()

    def _advance_from_priority_phase(self) -> list:
        gs = self.game_state
        phase = gs.phase

        if phase == "UPKEEP":
            self._broadcast_phase_transition("DRAW")
            gs.phase = "DRAW"
            self._run_draw_step()
            self._broadcast_state()
            return self._grant_active_priority()

        if phase == "DRAW":
            self._broadcast_phase_transition("PRECOMBAT_MAIN")
            gs.phase = "PRECOMBAT_MAIN"
            self._broadcast_state()
            return self._grant_active_priority()

        if phase == "PRECOMBAT_MAIN":
            for combat_phase in self.COMBAT_PHASES:
                gs.phase = combat_phase
            self._broadcast_phase_transition("POSTCOMBAT_MAIN")
            gs.phase = "POSTCOMBAT_MAIN"
            self._broadcast_state()
            return self._grant_active_priority()

        if phase == "POSTCOMBAT_MAIN":
            self._broadcast_phase_transition("END_STEP")
            gs.phase = "END_STEP"
            self._broadcast_state()
            return self._grant_active_priority()

        if phase == "END_STEP":
            return self._run_cleanup()

        return []

    def _run_draw_step(self) -> None:
        active = self.game_state.players[self.game_state.active_player]
        
        # Skip drawing on the very first turn of the game
        if not (self.game_state.turn == 1 and self._is_first_player()):
            
            # If draw_cards(1) returns False, library is empty
            if not active.draw_cards(1):
                from handlers.rules import trigger_game_over
                
                # Winner is the opponent of the AP
                winner_id = self.game_state.opponent_id(self.game_state.active_player)
                loser_id = self.game_state.active_player
                
                trigger_game_over(
                    self.game_state, 
                    self.network_manager, 
                    winner_id=winner_id, 
                    loser_id=loser_id, 
                    reason="DECK_EMPTY"
                )

    def _is_first_player(self) -> bool:
        return self.game_state.active_player == min(self.game_state.players.keys())

    def _run_cleanup(self) -> list:
        self._broadcast_phase_transition("CLEANUP")
        gs = self.game_state
        gs.phase = "CLEANUP"

        for player in gs.players.values():
            while len(player.hand) > 7 and player.hand:
                player.library.append(player.hand.pop())

        if check_state_based_actions(gs, self.network_manager):
            return []

        gs.turn += 1
        gs.active_player = gs.opponent_id(gs.active_player)
        self._broadcast_phase_transition("UNTAP")
        gs.phase = "UNTAP"
        self._run_untap_step()
        self._broadcast_state()
        return self._advance_from_untap()
