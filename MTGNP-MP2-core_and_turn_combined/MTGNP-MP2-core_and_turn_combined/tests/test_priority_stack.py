import pytest

from models.game_state import GameState
from models.player import Player
from priority_stack.stack_manager import StackManager
from turn_engine.trigger_manager import TriggerManager
from priority_stack.priority_manager import PriorityManager


@pytest.fixture
def game_state():
    gs = GameState()
    gs.players = {"Alice": Player("Alice"), "Bob": Player("Bob")}
    gs.active_player = "Alice"
    gs.phase = "PRECOMBAT_MAIN"
    gs.players["Alice"].hand = ["lightning_bolt_001"]
    return gs


@pytest.fixture
def stack_manager():
    return StackManager()


def test_push_cast_spell(game_state, stack_manager):
    pdu = {"type": "CAST_SPELL", "seq_num": 1, "card_id": "lightning_bolt_001"}
    ok, error_code, pdus = stack_manager.push_action(game_state, "Alice", pdu)

    assert ok is True
    assert error_code is None
    assert len(game_state.stack) == 1
    assert pdus[0]["type"] == "STACK_PUSH"


def test_push_cast_spell_illegal_card(game_state, stack_manager):
    pdu = {"type": "CAST_SPELL", "seq_num": 1, "card_id": "missing_card"}
    ok, error_code, _ = stack_manager.push_action(game_state, "Alice", pdu)

    assert ok is False
    assert error_code == "ILLEGAL_ACTION"


def test_resolve_top_moves_spell_to_graveyard(game_state, stack_manager):
    game_state.stack.append(
        {
            "object_id": "stack_1",
            "type": "SPELL",
            "source_id": "lightning_bolt_001",
            "controller": "Alice",
        }
    )

    pdus = stack_manager.resolve_top(game_state)

    assert game_state.stack == []
    assert "lightning_bolt_001" not in game_state.players["Alice"].hand
    assert "lightning_bolt_001" in game_state.players["Alice"].graveyard
    assert pdus[0]["type"] == "STACK_RESOLVE"


def test_priority_pass_switches_holder(game_state, stack_manager):
    trigger_manager = TriggerManager(stack_manager)
    closed = []

    def priority_window_closes(state):
        closed.append(state.phase)
        return []

    pm = PriorityManager(stack_manager, trigger_manager, priority_window_closes)
    grant = pm.grant_priority(game_state, "Alice")

    assert grant["type"] == "PRIORITY_GRANT"
    assert game_state.priority_holder == "Alice"

    pass_pdu = {"type": "PRIORITY_PASS", "seq_num": grant["seq_num"]}
    out = pm.handle_client_pdu(game_state, "Alice", pass_pdu)

    assert out[-1]["player_id"] == "Bob"
    assert game_state.priority_holder == "Bob"


def test_both_pass_empty_stack_closes_window(game_state, stack_manager):
    trigger_manager = TriggerManager(stack_manager)
    closed = []

    def priority_window_closes(state):
        closed.append(True)
        return [{"type": "PHASE_ADVANCE", "seq_num": 99, "player_id": "Alice"}]

    pm = PriorityManager(stack_manager, trigger_manager, priority_window_closes)
    grant = pm.grant_priority(game_state, "Alice")

    pm.handle_client_pdu(game_state, "Alice", {"type": "PRIORITY_PASS", "seq_num": grant["seq_num"]})
    bob_grant = pm.grant_priority(game_state, "Bob", reset_pass=False)
    out = pm.handle_client_pdu(game_state, "Bob", {"type": "PRIORITY_PASS", "seq_num": bob_grant["seq_num"]})

    assert closed == [True]
    assert out[0]["type"] == "PHASE_ADVANCE"


def test_stale_priority_token_rejected(game_state, stack_manager):
    trigger_manager = TriggerManager(stack_manager)
    pm = PriorityManager(stack_manager, trigger_manager, lambda _state: [])
    pm.grant_priority(game_state, "Alice")

    out = pm.handle_client_pdu(
        game_state,
        "Alice",
        {"type": "PRIORITY_PASS", "seq_num": 999},
    )

    assert out[0]["type"] == "ERROR"
    assert out[0]["code"] == "STALE_ACTION"
    assert out[1]["type"] == "PRIORITY_GRANT"


def test_trigger_order_response(game_state, stack_manager):
    trigger_manager = TriggerManager(stack_manager)
    game_state.pending_triggers = [
        {"trigger_id": "t1", "source_id": "s1", "controller": "Alice"},
        {"trigger_id": "t2", "source_id": "s2", "controller": "Alice"},
    ]

    out = trigger_manager.handle_order_response(
        game_state,
        {"ordered_trigger_ids": ["t2", "t1"]},
    )

    assert game_state.pending_triggers == []
    assert out[0]["type"] == "STACK_PUSH"
    assert len(out) == 2
