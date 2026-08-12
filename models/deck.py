from typing import List

class Deck:
    """
    Represents a player's submitted deck list.
    """
    def __init__(self, card_ids: List[str]):
        self.card_ids = card_ids

    def is_valid(self) -> bool:
        """
        Validates that the deck contains between 1 and 50 cards.
        """
        return 1 <= len(self.card_ids) <= 50