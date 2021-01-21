from enum import Enum
from typing import Dict, List, Callable

import discord

from games.GamePlayer import GamePlayer
from games.GameHasTimeout import GameWithTimeout
from games.round.RoundAction import RoundAction
from games.round.RoundGame import RoundGame
from games.game_modules.uno import registry
from games.game_modules.uno.registry import CardInstance


class State(Enum):
    CARD_PICK = 0
    FILL_ATTRIBUTES = 1

class UnoGamePlayer(GamePlayer):
    def __init__(self, user, bound_channel):
        super().__init__(user, bound_channel)
        self.hand = []

    def draw_n_cards(self, quantity: int, add_last=True):
        global_deck = self.game_instance.global_deck
        ret = []
        for i in range(quantity):
            ret.append(global_deck.pop())
        self.game_instance.add_round_action(GetCardAction(self, quantity))

        if add_last:
            self.hand.extend(ret)
        else:
            self.hand.extend(ret[:-1])

        return ret

    def draw_until(self, condition: Callable[[CardInstance], bool], add_last=True):
        global_deck = self.game_instance.global_deck
        ret = []
        while not condition(global_deck[-1]):
            ret.append(global_deck.pop())
        ret.append(global_deck.pop())
        self.game_instance.add_round_action(GetCardAction(self, len(ret)))

        if add_last:
            self.hand.extend(ret)
        else:
            self.hand.extend(ret[:-1])

        return ret

class UnoGame(RoundGame):
    game_name = "uno"
    game_player_class = UnoGamePlayer

    def __init__(self, cog, channel, players, settings):
        super().__init__(cog, channel, players, settings)

        self.state = None  # holds the game current state
        self.players_decks: Dict[int, List[CardInstance]] = {}
        self.global_deck = registry.generate_deck()
        self.last_played = None

        self.cards_to_take = 0

        self.selected_card = None

        self.attributes = {}
        self.requested_attributes = None
        self.filling_attribute = None
        self.attribute_request_type = None
        self.bound_message = None

    async def on_start(self):
        await super(UnoGame, self).on_start()
        for player in self.players:
            for i in range(7):
                player.hand.append(self.global_deck.pop())

        self.last_played = self.global_deck.pop()
        await self.last_played.force_place(self)

    async def timeout_round(self):
        await self.draw_cards(True)

    async def begin_round(self):
        if len(self.global_deck) < 10:
            self.global_deck.extend(self.generate_deck())
            await self.send("Deck has been regenerated")
        tmp = f'get {self.cards_to_take} cards' if self.cards_to_take > 0 else 'skip'

        current_player_embed = discord.Embed(title="It's your turn",
                                             description=f"pick a card or {tmp} by typing 'skip'",
                                             color=0x00ff00)
        current_player_embed.add_field(name="Current Card",
                                       value=self.last_played.get_user_friendly(),
                                       inline=False)
        current_player_embed.add_field(name="Your Deck",
                                       value=self.list_deck(self.current_player.hand),
                                       inline=False)

        other_players_embed = discord.Embed(title=f"It's {self.current_player.display_name}'s Turn",
                                            description="They're Picking A Card", color=0x00ff00)

        await self.excluding(self.current_player).send(embed=other_players_embed)
        await self.current_player.send(embed=current_player_embed)

        self.state = State.CARD_PICK

    def is_win(self):
        return len(self.current_player.hand) == 0

    async def on_message(self, message, player):
        if player.id == self.current_player.id:
            # the message is from current player
            if self.state == State.CARD_PICK:
                # this code will only run if the player is picking a card
                try:
                    selection = int(message.content)
                except ValueError:
                    if message.content.lower() == "skip":
                        await self.draw_cards()
                else:
                    if 0 <= selection < len(self.current_player.hand):
                        selected_card = self.current_player.hand[selection]

                        allowed = self.last_played.other_place_attempt(selected_card, self)

                        if allowed:
                            self.round_timeout += 5
                            self.current_player.hand.pop(selection)
                            await self.pick_card(selected_card)
                        else:
                            await self.current_player.send("You can't play that card")
                    else:
                        await self.current_player.send("You picked an invalid card")
            elif self.state == State.FILL_ATTRIBUTES:
                await self.attribute_request_type.on_message(self, message)

    async def on_reaction_add(self, reaction, player):
        if self.state == State.FILL_ATTRIBUTES:
            await self.attribute_request_type.on_reaction_add(self, reaction, player)

    def list_deck(self, deck):
        ret = []
        for idx, card in enumerate(deck):
            if self.last_played.other_place_attempt(card, self):
                ret.append(f"__`{idx}: `__{card.get_user_friendly()}")
            else:
                ret.append(f"`{idx}: `{card.get_user_friendly()}")
        return "\n".join(ret)

    async def pick_card(self, card):
        self.selected_card = card
        self.add_round_action(PickCardAction(self.current_player, self.selected_card))
        self.attributes = {}
        self.requested_attributes = self.selected_card.required_attributes()
        self.state = State.FILL_ATTRIBUTES
        if len(self.requested_attributes) > 0:
            await self.update_round_actions()
        await self.next_attribute_filling()

    async def next_attribute_filling(self):
        if len(self.requested_attributes) > 0:
            self.filling_attribute = list(self.requested_attributes.keys())[0]
            self.attribute_request_type = self.requested_attributes[self.filling_attribute]
            del self.requested_attributes[self.filling_attribute]

            await self.attribute_request_type.begin(self)
        else:
            await self.play_card()

    async def draw_cards(self, forced=False):
        if self.cards_to_take == 0:
            drawn_cards = self.current_player.draw_until(lambda c: self.last_played.other_place_attempt(c, self), False)
            if forced:
                self.last_played = drawn_cards[-1]
                await self.last_played.force_place(self)
                self.add_round_action(PickCardAction(self.current_player, self.last_played))
                self.add_round_action(PlayCardAction(self.current_player, self.last_played))
                await self.end_round()
            else:
                await self.pick_card(drawn_cards[-1])
        else:
            self.current_player.draw_n_cards(self.cards_to_take)
            self.cards_to_take = 0
            await self.end_round()

    async def play_card(self):
        """plays the selected card and ends the round"""
        self.last_played = self.selected_card
        await self.selected_card.place(self, self.attributes)
        self.add_round_action(PlayCardAction(self.current_player, self.selected_card))
        await self.end_round()

class GetCardAction(RoundAction):
    def __init__(self, player, number):
        super().__init__(player)
        self.number = number

    def represent(self, is_first_person) -> str:
        return f"get{'' if is_first_person else 's'} {self.number} card{'' if self.number == 1 else 's'}"


class PickCardAction(RoundAction):
    def __init__(self, player, card):
        super().__init__(player)
        self.card = card

    def represent(self, is_first_person) -> str:
        return f"select{'' if is_first_person else 's'} {self.card.get_user_friendly()}"

class PlayCardAction(RoundAction):
    def __init__(self, player, card):
        super().__init__(player)
        self.card = card

    def represent(self, is_first_person) -> str:
        return f"play{'' if is_first_person else 's'} {self.card.get_user_friendly()}"
