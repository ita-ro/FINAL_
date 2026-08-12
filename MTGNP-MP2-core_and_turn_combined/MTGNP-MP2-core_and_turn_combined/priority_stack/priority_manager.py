"""Priority ownership, passing, and action routing."""

from shared.pdu import make_pdu, next_seq
from priority_stack.stack_manager import StackManager
from turn_engine.trigger_manager import TriggerManager


class PriorityManager:
    def __init__(self, stack_manager: StackManager, trigger_manager: TriggerManager, priority_window_closes):
        self.stack = stack_manager
        self.triggers = trigger_manager
        self.priority_window_closes = priority_window_closes

    def grant_priority(self, state, player_id: str, reset_pass: bool = True, reuse_seq=None) -> dict:
        seq = reuse_seq if reuse_seq is not None else next_seq(state)
        pdu = {
            "type": "PRIORITY_GRANT",
            "seq_num": seq,
            "player_id": player_id,
            "time_limit_ms": 60000,
        }
        state.priority_holder = player_id
        state.priority_token = seq
        if reset_pass:
            state.last_pass_by = None
        return pdu

    def reissue(self, state):
        return {
            "type": "PRIORITY_GRANT",
            "seq_num": state.priority_token,
            "player_id": state.priority_holder,
            "time_limit_ms": 60000,
        }

    def _other_player(self, state, player_id: str) -> str:
        return state.opponent_id(player_id)

    def handle_client_pdu(self, state, player_id: str, pdu: dict) -> list:
        pdu_type = pdu.get("type")

        if player_id != state.priority_holder:
            return [
                make_pdu(
                    state,
                    "ERROR",
                    code="NOT_YOUR_PRIORITY",
                    message="You do not hold priority",
                    rejected_action=pdu,
                )
            ]

        if pdu.get("seq_num") != state.priority_token:
            return [
                make_pdu(
                    state,
                    "ERROR",
                    code="STALE_ACTION",
                    message=(
                        f"Priority token mismatch. Expected seq_num "
                        f"{state.priority_token}, got {pdu.get('seq_num')}."
                    ),
                    rejected_action=pdu,
                ),
                self.reissue(state),
            ]

        if pdu_type == "PRIORITY_PASS":
            return self._handle_pass(state, player_id)

        if pdu_type in ("CAST_SPELL", "ACTIVATE_ABILITY"):
            return self._handle_stack_action(state, player_id, pdu)

        if pdu_type == "PLAY_LAND":
            return self._handle_play_land(state, player_id, pdu)

        if pdu_type == "TRIGGER_ORDER_RESPONSE":
            out = self.triggers.handle_order_response(state, pdu)
            return self._after_trigger_step(state, out)

        if pdu_type == "TRIGGER_CHOICE_RESPONSE":
            out = self.triggers.handle_choice_response(state, pdu)
            return self._after_trigger_step(state, out)

        return [
            make_pdu(
                state,
                "ERROR",
                code="UNKNOWN_TYPE",
                message=f"Unhandled type: {pdu_type}",
                rejected_action=pdu,
            ),
            self.reissue(state),
        ]

    def _handle_pass(self, state, player_id: str) -> list:
        out = []
        opponent = self._other_player(state, player_id)

        if state.last_pass_by == opponent:
            if state.stack:
                resolve_out = self.stack.resolve_top(state)
                out.extend(resolve_out)

                if any(p.get("type") == "GAME_OVER" for p in resolve_out):
                    return out

                out.extend(self._check_triggers_then_grant(state, reuse_seq=out[-1]["seq_num"] if out else None))
                return out

            out.extend(self.priority_window_closes(state))
            return out

        state.last_pass_by = player_id
        out.append(self.grant_priority(state, opponent, reset_pass=False))
        return out

    def _handle_stack_action(self, state, player_id: str, pdu: dict) -> list:
        ok, error_code, pdus = self.stack.push_action(state, player_id, pdu)
        if not ok:
            return [
                make_pdu(
                    state,
                    "ERROR",
                    code=error_code,
                    message="Action rejected.",
                    rejected_action=pdu,
                ),
                self.reissue(state),
            ]

        out = list(pdus)
        seq = out[-1]["seq_num"] if out else state.priority_token
        out.append(self.grant_priority(state, player_id, reuse_seq=seq))
        return out

    def _handle_play_land(self, state, player_id: str, pdu: dict) -> list:
        handler = getattr(self, "play_land_handler", None)
        if handler is None:
            return [
                make_pdu(
                    state,
                    "ERROR",
                    code="ILLEGAL_ACTION",
                    message="Land-play handling is not connected yet.",
                    rejected_action=pdu,
                ),
                self.reissue(state),
            ]

        ok, error_code, pdus = handler(state, player_id, pdu)
        if not ok:
            return [
                make_pdu(
                    state,
                    "ERROR",
                    code=error_code,
                    message="Land play rejected",
                    rejected_action=pdu,
                ),
                self.reissue(state),
            ]

        out = list(pdus)
        seq = out[-1]["seq_num"] if out else state.priority_token
        out.append(self.grant_priority(state, player_id, reuse_seq=seq))
        return out

    def _check_triggers_then_grant(self, state, reuse_seq=None) -> list:
        triggers = self.triggers.get_pending_triggers(state)
        if not triggers:
            return [self.grant_priority(state, state.active_player, reuse_seq=reuse_seq)]

        out = self.triggers.place_on_stack(state, triggers)
        if state.pending_triggers:
            return out

        seq = out[-1]["seq_num"] if out else reuse_seq
        out.append(self.grant_priority(state, state.active_player, reuse_seq=seq))
        return out

    def _after_trigger_step(self, state, out: list) -> list:
        out = list(out)
        seq = out[-1]["seq_num"] if out else None
        out.append(self.grant_priority(state, state.active_player, reuse_seq=seq))
        return out
