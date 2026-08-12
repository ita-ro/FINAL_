import random

from shared.pdu import make_pdu
from shared.catalog import CardDatabase

def handle_player_ready(pdu, client_socket, game_state, network_manager):
    """
    Processes the PLAYER_READY message, validates the deck, 
    and triggers GAME_SETUP if both players are ready.
    """
    # Use .strip() to catch whitespace-only strings
    player_id = str(pdu.get("player_id", "")).strip()
    deck_list = pdu.get("deck_list", [])

    # 1. Server Responsibility: Reject Empty Player ID
    if not player_id:
        error_msg = {
            "type": "ERROR",
            "seq_num": pdu.get("seq_num"),
            "code": "ILLEGAL_ACTION",
            "message": "player_id must not be an empty string.",
            "rejected_action": pdu
        }
        network_manager.send_message(client_socket, error_msg)
        return
    
    # Deck Validation
    if not (1 <= len(deck_list) <= 50):
        error_msg = {
            "type": "ERROR",
            "seq_num": pdu.get("seq_num"),
            "code": "ILLEGAL_DECK",
            "message": f"Deck contains {len(deck_list)} cards; maximum is 50.",
            "rejected_action": pdu
        }
        network_manager.send_message(client_socket, error_msg)
        return

    # Validate that every card is in the legal card set
    illegal_cards = [
        card_id for card_id in deck_list
        if not CardDatabase.get_card(card_id)
    ]

    if illegal_cards:
        error_msg = {
            "type": "ERROR",
            "seq_num": pdu.get("seq_num"),
            "code": "ILLEGAL_DECK",
            "message": f"Unknown card IDs: {illegal_cards}",
            "rejected_action": pdu
        }
        network_manager.send_message(client_socket, error_msg)
        return

    # Checks for duplicate player IDs
    if player_id in game_state.players:
        error_msg = {
            "type": "ERROR",
            "seq_num": pdu.get("seq_num"),
            "code": "DUPLICATE_ID",
            "message": f"Player ID '{player_id}' is already claimed.",
            "rejected_action": pdu
        }
        network_manager.send_message(client_socket, error_msg)
        return

    # Update the GameState with the new player and their deck
    player = game_state.add_player(player_id)
    player.library = deck_list.copy()
    player.is_ready = True
    
    # Check state transition condition
    ready_players = [p for p in game_state.players.values() if p.is_ready]
    
    if len(ready_players) < 2:
        # Still waiting in lobby -> Broadcast lobby state
        update_msg = make_pdu(
            game_state,
            "GAME_STATE_UPDATE",
            state = game_state.get_visible_state(player_id)
        )
        network_manager.send_message(client_socket, update_msg)
    
    else:
        # Game setup State Transition
        _execute_game_setup(game_state)
        
        for pid in game_state.players.keys():
            target_socket = network_manager.get_socket_for_player(pid)
            update_msg = make_pdu(
                game_state, "GAME_STATE_UPDATE", state = game_state.get_visible_state(pid)
            )
            game_state.players[pid].expected_mulligan_seq = update_msg["seq_num"] # <--- RESTORED
            network_manager.send_message(target_socket, update_msg)

def _execute_game_setup(game_state):
    """
    Performs the automated setup operations outlined in Section 6.3 
    and transitions the game to the MULLIGAN phase.
    """
    game_state.phase = "MULLIGAN"
    
    # Determine who goes first (random coin flip)
    player_ids = list(game_state.players.keys())
    game_state.active_player = random.choice(player_ids)
    
    # Initialize both players
    for player in game_state.players.values():
        player.life_total = 20
        player.is_ready = False
        
        # Shuffle the library
        random.shuffle(player.library)
        
        # Draw initial 7 cards
        draw_count = min(7, len(player.library))
        player.hand = player.library[:draw_count]
        player.library = player.library[draw_count:]

def handle_mulligan_choice(pdu, client_socket, game_state, network_manager, turn_manager=None):
    """
    Processes a player's mulligan decision.
    Validates the London Mulligan rule and transitions to IN_GAME when both keep.
    """
    # Assuming network_manager maps sockets to player_ids
    player_id = network_manager.get_player_id(client_socket)
    player = game_state.players[player_id]
    
    expected_seq = getattr(player, 'expected_mulligan_seq', None)
    if expected_seq is not None and pdu.get("seq_num") != expected_seq:
        error_msg = {
            "type": "ERROR", "seq_num": pdu.get("seq_num"),
            "code": "STALE_ACTION", "message": f"Expected seq_num {expected_seq}.",
            "rejected_action": pdu
        }
        network_manager.send_message(client_socket, error_msg)
        return
    
    keep = pdu.get("keep", True)
    cards_to_bottom = pdu.get("cards_to_bottom", [])
    
    if not keep:
        # Player takes a mulligan
        player.mulligan_count += 1
        
        # Return current hand and previously drawn cards to library, then shuffle
        player.library.extend(player.hand)
        player.hand.clear()
        import random
        random.shuffle(player.library)
        
        # Draw a fresh hand of 7
        draw_count = min(7, len(player.library))
        player.hand = player.library[:draw_count]
        player.library = player.library[draw_count:]
        
        # Send updated state to this specific player
        update_msg = make_pdu(
            game_state, "GAME_STATE_UPDATE", state = game_state.get_visible_state(player_id)
        )
        player.expected_mulligan_seq = update_msg["seq_num"]
        network_manager.send_message(client_socket, update_msg)
        
        return

    # Player keeps -> Validate the mulligan constraints
    if len(cards_to_bottom) != player.mulligan_count:
        error_msg = {
            "type": "ERROR",
            "seq_num": pdu.get("seq_num"),
            "code": "ILLEGAL_ACTION",
            "message": f"Must bottom exactly {player.mulligan_count} cards.",
            "rejected_action": pdu
        }
        network_manager.send_message(client_socket, error_msg)
        return
        
    # Validate that all chosen cards are actually in the player's hand
    for card_id in cards_to_bottom:
        if card_id not in player.hand:
            error_msg = {
                "type": "ERROR",
                "seq_num": pdu.get("seq_num"),
                "code": "ILLEGAL_ACTION",
                "message": f"Card {card_id} is not in your hand.",
                "rejected_action": pdu
            }
            network_manager.send_message(client_socket, error_msg)
            return

    # Remove chosen cards from hand and put on bottom of library
    for card_id in cards_to_bottom:
        player.hand.remove(card_id)
        player.library.append(card_id)  # Appending adds to the "bottom" (end of list)
        
    player.is_ready = True  # Mulligan complete
    
    # Check if both players have kept their hands
    ready_players = [p for p in game_state.players.values() if p.is_ready]
    
    if len(ready_players) == 2:
        # Transition to in-game and begin the first turn
        game_state.phase = "IN_GAME"
        game_state.turn = 1

        for p in game_state.players.values():
            p.is_ready = False

        for pid in game_state.players.keys():
            target_socket = network_manager.get_socket_for_player(pid)
            update_msg = make_pdu(
                game_state,
                "GAME_STATE_UPDATE",
                state = game_state.get_visible_state(pid)
            )
            network_manager.send_message(target_socket, update_msg)

        if turn_manager is not None:
            turn_manager.begin_game()