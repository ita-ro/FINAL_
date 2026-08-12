from typing import List
from models.card import Permanent

class Player:
    """
    Represents a single user and their personal game zones.
    """
    def __init__(self, player_id: str):
        self.player_id = player_id
        self.life_total = 20
        
        # Game zones
        self.library: List[str] = []
        self.hand: List[str] = []
        self.graveyard: List[str] = []
        self.battlefield: List[Permanent] = []

        # Tracks state
        self.is_ready = False
        self.mulligan_count = 0
        self.has_played_land_this_turn = False

    def draw_cards(self, count: int = 1) -> bool:
        """
        Draws cards from the top of the library to the hand.
        Returns False if the player attempts to draw from an empty library.
        """
        for _ in range(count):
            if not self.library:
                return False  # Signals the GameState to trigger game over
            
            # Pop index 0 or the top of the deck
            drawn_card = self.library.pop(0)
            self.hand.append(drawn_card)
            
        return True

    def adjust_life(self, amount: int):
        """
        Adjusts life total. (Negative amount for damage/loss, positive for gain).
        """
        self.life_total += amount

    def reset_for_new_turn(self):
        """
        Clears flags at the start of the Untap Step.
        """
        self.has_played_land_this_turn = False