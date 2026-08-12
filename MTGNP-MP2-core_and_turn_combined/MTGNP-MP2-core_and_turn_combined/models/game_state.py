from typing import Dict, Optional, List
from models.player import Player

class GameState:
    """
    The master game state maintained by the server.
    """
    def __init__(self):
        self.phase = "LOBBY"
        self.turn = 0
        self.players: Dict[str, Player] = {}
        self.active_player: Optional[str] = None
        self.priority_holder: Optional[str] = None
        self.priority_token: Optional[int] = None
        self.last_pass_by: Optional[str] = None
        self.pending_triggers: List[dict] = []
        self.stack: List[dict] = []
        self.seq_counter = 0

    def opponent_id(self, player_id: str) -> Optional[str]:
        """Return the opposing player's ID in a two-player game."""
        for pid in self.players:
            if pid != player_id:
                return pid
        return None

    @property
    def non_active_player(self) -> Optional[str]:
        if self.active_player is None:
            return None
        return self.opponent_id(self.active_player)
        
    def add_player(self, player_id: str) -> Player:
        """Adds a new player to the game state."""
        if player_id not in self.players:
            self.players[player_id] = Player(player_id)
        return self.players[player_id]
            
    def get_visible_state(self, requesting_player_id: str) -> dict:
        """
        Generates the GAME_STATE_UPDATE payload for a specific player.
        """
        # Handle the simplified lobby state format
        if self.phase == "LOBBY":
            return {
                "phase": "LOBBY",
                "players_ready": sum(1 for p in self.players.values() if p.is_ready),
                "waiting_for": [p.player_id for p in self.players.values() if not p.is_ready]
            }
            
        # Identify the opponent to mask their hand
        opponent_id = next((pid for pid in self.players if pid != requesting_player_id), None)
        requesting_player = self.players[requesting_player_id]
        opponent = self.players.get(opponent_id) if opponent_id else None

        # Build the in-game state dictionary
        state = {
            "turn": self.turn,
            "active_player": self.active_player,
            "phase": self.phase,
            "priority_holder": self.priority_holder,
            "life_totals": {pid: p.life_total for pid, p in self.players.items()},
            "stack": self.stack,
            "battlefield": {pid: [perm.to_dict() for perm in p.battlefield] for pid, p in self.players.items()},
            "graveyard": {pid: p.graveyard for pid, p in self.players.items()},
            
            # Visible hand for the requesting player
            "hand": {requesting_player_id: requesting_player.hand},
            
            # Hidden info for the opponent
            "hand_counts": {opponent_id: len(opponent.hand)} if opponent else {},
            
            "library_counts": {pid: len(p.library) for pid, p in self.players.items()},
            "land_played_this_turn": requesting_player.has_played_land_this_turn 
        }
        
        return state
    