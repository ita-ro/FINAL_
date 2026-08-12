ERROR_CODES = {
    "INVALID_JSON",
    "ILLEGAL_DECK",
    "UNKNOWN_TYPE",
    "STALE_ACTION",
    "NOT_YOUR_PRIORITY",
    "ILLEGAL_ACTION",
    "ILLEGAL_TARGET",
    "TRIGGER_ORDER_INVALID",
    "TRIGGER_CHOICE_INVALID",
    "INSUFFICIENT_MANA",
    "WRONG_PHASE",
    "DUPLICATE_ID",
}

def create_error(code, message, rejected_action = None, seq_num = None):
    """
    Creates an MTGNP ERROR PDU.
    """

    if code not in ERROR_CODES:
        raise ValueError(f"Unknown MTGNP error code: {code}")

    error = {
        "type": "ERROR",
        "seq_num": seq_num,
        "code": code,
        "message": message,
    }

    if rejected_action is not None:
        error["rejected_action"] = rejected_action

    return error