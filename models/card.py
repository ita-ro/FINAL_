from shared.catalog import CardDatabase

class Card:
    """
    Represents a generic card ID.
    """
    def __init__(self, card_id: str):
        self.card_id = card_id


class Permanent:
    """
    Represents a playing card on the battlefield. Pulls data from CardDatabase.
    """
    def __init__(self, card_id: str):
        self.id = card_id
        self.tapped = False
        
        card_data = CardDatabase.get_card(card_id)
        
        # Check if this card is a creature
        is_creature = "Creature" in card_data.get("type", "")
        
        if is_creature:
            self.damage = 0
            self.power = card_data.get("power", 0)
            self.toughness = card_data.get("toughness", 0)
            
            # Haste check
            effect_text = card_data.get("effect", "")
            if "Haste" in effect_text:
                self.summoning_sick = False
            else:
                self.summoning_sick = True
            
    def to_dict(self):
        """
        Serializes the permanent for the GAME_STATE_UPDATE payload.
        """
        data = {"id": self.id, "tapped": self.tapped}
        
        # Only append creature stats if it is a creature
        if hasattr(self, 'damage'):
            data.update({
                "damage": self.damage,
                "power": self.power,
                "toughness": self.toughness,
                "summoning_sick": self.summoning_sick
            })
        return data