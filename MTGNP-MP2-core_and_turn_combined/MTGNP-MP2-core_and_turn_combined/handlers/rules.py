def check_state_based_actions(game_state, network_manager):
    """
    Evaluates win/loss conditions and creature states.
    Returns True if game is over, False otherwise.
    """
    if game_state.phase not in ["IN_GAME", "COMBAT_DAMAGE", "END_OF_COMBAT", "PRECOMBAT_MAIN", "POSTCOMBAT_MAIN", "UPKEEP", "DRAW", "END_STEP", "CLEANUP"]:
        return False

    loser_id = None
    winner_id = None
    reason = None

    player_ids = list(game_state.players.keys())
    if len(player_ids) != 2:
        return False

    p1_id, p2_id = player_ids[0], player_ids[1]
    p1 = game_state.players[p1_id]
    p2 = game_state.players[p2_id]

    # Check Win/Loss Conditions 
    p1_dead = p1.life_total <= 0
    p2_dead = p2.life_total <= 0

    if p1_dead and p2_dead:
        # Simultaneous death: Active Player loses
        loser_id = game_state.active_player
        winner_id = p2_id if loser_id == p1_id else p1_id
        reason = "LIFE_ZERO"
    elif p1_dead:
        loser_id = p1_id
        winner_id = p2_id
        reason = "LIFE_ZERO"
    elif p2_dead:
        loser_id = p2_id
        winner_id = p1_id
        reason = "LIFE_ZERO"

    # Trigger game over if a win condition was met
    if winner_id and loser_id:
        trigger_game_over(game_state, network_manager, winner_id, loser_id, reason)
        return True

    # Process Creature SBAs
    for player in game_state.players.values():
        surviving_creatures = []
        for perm in player.battlefield:
            if hasattr(perm, 'toughness'):
                # Move to graveyard if toughness is <= 0 or damage >= toughness
                if perm.toughness <= 0 or perm.damage >= perm.toughness:
                    player.graveyard.append(perm.id)
                else:
                    surviving_creatures.append(perm)
            else:
                surviving_creatures.append(perm)
        
        # Update the battlefield to only include surviving permanents
        player.battlefield = surviving_creatures

    return False


def trigger_game_over(game_state, network_manager, winner_id, loser_id, reason):
    """
    Constructs the GAME_OVER PDU, broadcasts it, and resets the server to LOBBY.
    """
    game_over_msg = {
        "type": "GAME_OVER",
        "seq_num": network_manager.get_next_seq_num(),
        "winner_id": winner_id,
        "loser_id": loser_id,
        "reason": reason
    }
    
    # Broadcast to all connected clients
    for pid in game_state.players.keys():
        target_socket = network_manager.get_socket_for_player(pid)
        if target_socket:
            network_manager.send_message(target_socket, game_over_msg)

    # Reset the GameState for a new match
    game_state.phase = "LOBBY"
    game_state.turn = 0
    game_state.stack.clear()
    game_state.active_player = None
    game_state.priority_holder = None
    
    # Fully clear the players dictionary so IDs are reset
    game_state.players.clear()

def handle_concede(pdu, client_socket, game_state, network_manager):
        """
        Processes a CONCEDE PDU and immediately triggers GAME_OVER.
        """
        loser_id = pdu.get("player_id")
        
        # Identify the winner
        winner_id = next((pid for pid in game_state.players if pid != loser_id), None)
        
        if winner_id:
            trigger_game_over(game_state, network_manager, winner_id, loser_id, "CONCEDE")