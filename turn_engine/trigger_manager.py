"""Triggered ability detection, ordering, and stack placement."""

from shared.pdu import make_pdu
from priority_stack.stack_manager import StackManager


class TriggerManager:
    def __init__(self, stack_manager: StackManager):
        self.stack = stack_manager

    def get_pending_triggers(self, state) -> list:
        # Placeholder: full battlefield scanning requires catalog integration.
        return []

    def place_on_stack(self, state, triggers: list) -> list:
        out = []
        ap = [t for t in triggers if t["controller"] == state.active_player]
        nap = [t for t in triggers if t["controller"] != state.active_player]

        for group in (ap, nap):
            if len(group) >= 2:
                owner = group[0]["controller"]
                out.append(
                    make_pdu(
                        state,
                        "TRIGGER_ORDER",
                        player_id=owner,
                        trigger_ids=[t["trigger_id"] for t in group],
                    )
                )
                state.pending_triggers = group
                return out
            for trig in group:
                out += self._maybe_push(state, trig)
        return out

    def handle_order_response(self, state, pdu: dict) -> list:
        ordered_ids = pdu.get("ordered_trigger_ids", [])
        pending_ids = {t["trigger_id"] for t in state.pending_triggers}

        if set(ordered_ids) != pending_ids:
            return [
                make_pdu(
                    state,
                    "ERROR",
                    code="TRIGGER_ORDER_INVALID",
                    message="Response must list exactly the requested trigger IDs.",
                    rejected_action=pdu,
                )
            ]

        by_id = {t["trigger_id"]: t for t in state.pending_triggers}
        out = []
        for tid in ordered_ids:
            out += self._maybe_push(state, by_id[tid])
        state.pending_triggers = []
        return out

    def handle_choice_response(self, state, pdu: dict) -> list:
        if not pdu.get("accept"):
            return []
        trig = {
            "source_id": pdu["trigger_id"],
            "controller": state.priority_holder,
            "targets": [pdu["chosen_target"]] if pdu.get("chosen_target") else [],
        }
        return self.stack.push_trigger(state, trig)

    def _maybe_push(self, state, trig: dict) -> list:
        if trig.get("optional"):
            return [
                make_pdu(
                    state,
                    "TRIGGER_CHOICE",
                    trigger_id=trig["trigger_id"],
                    source_id=trig["source_id"],
                    effect_summary=trig.get("effect_summary", ""),
                    requires_target=trig.get("requires_target", False),
                    legal_targets=trig.get("legal_targets", []),
                )
            ]
        return self.stack.push_trigger(state, trig)
