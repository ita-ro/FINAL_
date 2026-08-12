"""PDU construction helpers shared by turn engine and priority stack."""


def next_seq(state) -> int:
    """Return the next monotonic sequence number for outbound PDUs."""
    state.seq_counter += 1
    return state.seq_counter


def make_pdu(game_state, pdu_type: str, **kwargs) -> dict:
    """Build a protocol message with an auto-assigned seq_num."""
    pdu = {"type": pdu_type, "seq_num": next_seq(game_state)}
    pdu.update(kwargs)
    return pdu
