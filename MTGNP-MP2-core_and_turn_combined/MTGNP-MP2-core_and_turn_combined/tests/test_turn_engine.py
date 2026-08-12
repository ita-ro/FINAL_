from unittest.mock import MagicMock

from models.game_state import GameState
from models.player import Player
from models.card import Permanent
from turn_engine.turn_manager import TurnManager
from priority_stack.stack_manager import StackManager
from turn_engine.trigger_manager import TriggerManager
from priority_stack.priority_manager import PriorityManager


def _build_turn_manager():
    gs = GameState()
    gs.players = {
        "Alice": Player("Alice"),
        "Bob": Player("Bob"),
    }
    gs.players["Alice"].library = ["card_a", "card_b"]
    gs.players["Bob"].library = ["card_c"]
    gs.active_player = "Alice"

    network_manager = MagicMock()
    network_manager.get_next_seq_num.return_value = 1
    network_manager.get_socket_for_player.return_value = MagicMock()

    turn_manager = TurnManager(gs, network_manager)
    stack_manager = StackManager()
    trigger_manager = TriggerManager(stack_manager)
    priority_manager = PriorityManager(
        stack_manager,
        trigger_manager,
        turn_manager.priority_window_closes,
    )
    turn_manager.set_priority_manager(priority_manager)
    return turn_manager, gs, network_manager


def test_begin_game_enters_upkeep_and_grants_priority():
    turn_manager, gs, network_manager = _build_turn_manager()

    turn_manager.begin_game()

    assert gs.phase == "UPKEEP"
    assert gs.turn == 1
    assert gs.priority_holder == "Alice"
    assert network_manager.send_message.called


def test_untap_step_untaps_permanents():
    turn_manager, gs, _ = _build_turn_manager()
    permanent = Permanent("white_knight_002")
    permanent.tapped = True
    gs.players["Alice"].battlefield.append(permanent)
    gs.players["Alice"].has_played_land_this_turn = True

    turn_manager._run_untap_step()

    assert permanent.tapped is False
    assert gs.players["Alice"].has_played_land_this_turn is False


def test_priority_window_closes_advances_upkeep_to_draw():
    turn_manager, gs, _ = _build_turn_manager()
    gs.phase = "UPKEEP"
    gs.turn = 2

    out = turn_manager.priority_window_closes(gs)

    assert gs.phase == "DRAW"
    assert out[-1]["type"] == "PRIORITY_GRANT"


def test_draw_step_draws_for_active_player():
    turn_manager, gs, _ = _build_turn_manager()
    gs.phase = "DRAW"
    gs.turn = 2
    starting_hand = list(gs.players["Alice"].hand)

    turn_manager._run_draw_step()

    assert len(gs.players["Alice"].hand) == len(starting_hand) + 1
