from shared.pdu import make_pdu

class StackManager:
    """Manages the spell/ability stack and resolution."""

    def push_action(self, state, player_id: str, pdu: dict):
        pdu_type = pdu.get("type")
        card_id = pdu.get("card_id") or pdu.get("source_id")

        if pdu_type == "CAST_SPELL":
            if card_id not in state.players[player_id].hand:
                return False, "ILLEGAL_ACTION", []
            stack_obj = {
                "object_id": f"stack_{len(state.stack) + 1}",
                "type": "SPELL",
                "source_id": card_id,
                "controller": player_id,
                "targets": pdu.get("targets", [])
            }
        elif pdu_type == "ACTIVATE_ABILITY":
            stack_obj = {
                "object_id": f"stack_{len(state.stack) + 1}",
                "type": "ABILITY",
                "source_id": pdu.get("source_id"),
                "controller": player_id,
                "targets": pdu.get("targets", [])
            }
        else:
            return False, "UNKNOWN_TYPE", []

        state.stack.append(stack_obj)
        return True, None, [
            make_pdu(
                state,
                "STACK_PUSH",
                object_id=stack_obj["object_id"],
                object_type=stack_obj["type"],
                controller=player_id,
                source_id=stack_obj["source_id"],
            )
        ]

    def push_trigger(self, state, trig: dict):
        stack_obj = {
            "object_id": f"stack_{len(state.stack) + 1}",
            "type": "TRIGGER",
            "source_id": trig.get("source_id"),
            "controller": trig.get("controller"),
            "targets": trig.get("targets", []),
        }
        state.stack.append(stack_obj)
        return [
            make_pdu(
                state,
                "STACK_PUSH",
                object_id=stack_obj["object_id"],
                object_type="TRIGGER",
                controller=stack_obj["controller"],
                source_id=stack_obj["source_id"],
            )
        ]

    def resolve_top(self, state):
        if not state.stack:
            return []

        stack_obj = state.stack.pop()
        controller = stack_obj["controller"]
        pdus = [
            make_pdu(
                state,
                "STACK_RESOLVE",
                object_id=stack_obj["object_id"],
                controller=controller,
            )
        ]

        if stack_obj["type"] == "SPELL":
            card_id = stack_obj["source_id"]
            player = state.players[controller]
            if card_id in player.hand:
                player.hand.remove(card_id)
                player.graveyard.append(card_id)

        return pdus
