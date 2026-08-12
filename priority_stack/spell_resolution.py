"""
Spell Resolution:
execute the effect of a spell or ability when that 
object reaches the top of the stack and resolves, 
applies the appprorpriatee channges to the game 

Resolver:
  checks target legality at resolution
  applies the card's effect to GameState
  returns state_changes
"""


import re

from game_state import GameState, StackItem
from models.card import Permanent

class SpellResolver:

    def __init__(self, card_catalog: dict):
        self.catalog = card_catalog

    def _get_card(self, card_id: str) -> dict:
        # Get the card definition from the supplied catalog
        return self.catalog.get(card_id,{})

    def _find_permanent(self,state: GameState, permanent_id: str):
        #search every player's battlefield for a permanent
        
        for player_id, player in state.players.items():
            for permanent in player.battlefield:
                if permanent.id == permanent_id:
                    return player_id, permanent
        return None, None

    def _find_stack_item(self, state: GameState, stack_item_id: str):
        for stack_item in state.stack:
            if stack_item.stack_item_id == stack_item_id:
                return stack_item

        return None

    def _damage_amount(self, effect: str):
        #extract a fixed damage amount from the card's simplified effect text

        match = re.search(r"deals\s+(\d+)\s+damage", effect, flags=re.IGNORECASE)

        if match is None: 
            return None

        return int(match.group(1))

    #target legality
    def targets_still_legal(self, state: GameState, item: StackItem) -> bool:
            #checks whether the targets of a resolving StackItem are still legal

            card = self._get_card(item.source)

            if not card:
                return False

            effect = (card.get("effect") or "").lower()

            #no targets = nothing to check
            if not item.targets:
                return True

            #counter target spell
            if "counter target spell" in effect:

                for target_id in item.targets:
                    if self._find_stack_item(state, target_id) is None:
                        return False

                return True

            #any target/player target
            if("any target" in effect or "target player" in effect):
                for target_id in item.targets:

                    if target_id in state.players:
                        continue

                    _, permanent = self._find_permanent(state, target_id)

                    if permanent is None:
                        return False
                return True

            # target creature
            if "target creature" in effect:

                for target_id in item.targets:

                    _, permanent = self._find_permanent(state,target_id)

                    if permanent is None:
                        return False

                return True
            return True

    

    #spell resolution

    def apply (self, state : GameState, item: StackItem) -> list:
        #apply the effect of the resolving StackItem
        #returns a list of state-change dictionaries

        card = self._get_card(item.source)

        if not card:
            return []

        effect = (card.get("effect") or "").strip()
        effect_lower = effect.lower()

        changes = []

        damage_amount = self._damage_amount(effect)

        if damage_amount is not None:

            for target_id in item.targets:

                if target_id in state.players:

                    player = state.players[target_id]

                    player.adjust_life(-damage_amount)

                    changes.append({
                        "type" : "DAMAGE",
                        "target": target_id,
                        "amount": damage_amount
                    })

                    continue

        #damage creature
                _, permanent = self._find_permanent(state, target_id)


                if(permanent is not None and hasattr (permanent, "damage")):

                    permanent.damage += damage_amount

                    changes.append({
                        "type": "DAMAGE",
                        "target": target_id,
                        "amount": damage_amount
                    })

            return changes

        #counter target spell 

        if "counter target spell" in effect_lower:

            for target_id in item.targets:

                target = self._find_stack_item(state, target_id)

                if target is None:
                    continue

                state.stack.remove(target)

                changes.append({
                    "type" : "COUNTERED",
                    "stack_item_id" : target_id,
                })
            return changes

        #return target creature
        if (
            "return target creature" in effect_lower 
            and "owner's hand" in effect_lower
        ):

            for target_id in item.targets:

                owner_id, permanent = self._find_permanent(state, target_id)

                if permanent is None:
                    continue

                state.players[owner_id].battlefield.remove(permanent)

                state.players[owner_id].hand.append(permanent.id)

                changes.append({
                    "type": "PERMANENT_RETURNED",
                    "card_id": permanent.id,
                    "owner": owner_id
                })

            return changes

        #destroy

        if "destroy target" in effect_lower:

            for target_id in item.targets:
                owner_id, permanent = self._find_permanent(state, target_id)

                if permanent is None:
                    continue

                state.players[owner_id].battlefield.remove(permanent)

                state.players[owner_id].graveyard.append(permanent.id)

                changes.append({
                    "type" : "DESTROYED",
                    "card_id": permanent.id,
                    "owner": owner_id,
                })

            return changes

        #draw

        if "draw a card" in effect_lower:

            player = state.players.get(item.controller)

            if player is not None:

                if player.draw_cards(1):

                    changes.append({
                        "type" : "DRAW",
                        "player_id" : item.controller,
                        "count" : 1
                    })
            return changes

    
        #discard

        if "discard two cards" in effect_lower:

            targets = item.targets or [item.controller]

            for player_id in targets:

                player = state.players.get(player_id)

                if player is None:
                    continue

                discarded = []

                for _ in range (min(2,len(player.hand))):
                    card_id = player.hand.pop(0)

                    player.graveyard.append(card_id)

                    discarded.append(card_id)

                changes.append({
                    "type" : "DISCARD",
                    "target" : player_id,
                    "cards" : discarded
                })
            return changes

        #permanent spell 
        card_type = (card.get("type") or "").lower()

        if card_type in {
            "creature",
            "artifact",
            "enchantment",
            "land"
        }:
            player = state.players.get(item.controller)

            if player is None:
                return []

            permanent = Permanent(item.source)

            if("enters the battlefield tapped" 
                in effect_lower):

                permanent.tapped = True

            player.battlefield.append(permanent)

            changes.append({
                "type" : "PERMANENT_ENTERS",
                "card_id": item.source,
                "controller": item.controller,
                "tapped" : permanent.tapped
            })

            return changes

        changes.append({
            "type": "UNSUPPORTED_EFFECT",
            "source_id" : item.source,
            "effect": effect
        })

        return changes
        