import asyncio
from enum import Enum

import discord

from games.Game import Game, EndGame
from games.uno import registry
from games.uno.registry import Color, color_to_emoji, emoji_to_color


class State(Enum):
    CARD_PICK = 0
    FILL_ATTRIBUTES = 1


class UnoGame(Game):
    def __init__(self, cog, channel, players):
        super().__init__(cog, channel, players)
        self.state = None

        self.current_player_idx = 0
        self.direction = registry.Direction.UP_WARDS
        self.players_decks = {}
        self.global_deck = registry.generate_deck()
        self.played_deck = []
        self.cards_to_take = 0

        self.selected_card = None
        self.round_time = 20

        self.attributes = {}  # contains the final attributes
        self.filling_attribute = ""  # contains the attribute that is currently being filled in
        self.requested_attributes = {}  # contains all the remaining attributes the card asked
        self.bound_message = None  # contains the message that requests the player for the attribute
        self.attribute_request_type = None  # contains the type of the attribute that is being filled in

    async def on_start(self):
        for player in self.players:
            self.players_decks[player.id] = []
            for i in range(7):
                self.deck(player).append(self.global_deck.pop())

        self.played_deck.append(self.global_deck.pop())
        await self.played_deck[0].force_place(self)
        await self.round_start()

        while self.running:
            await asyncio.sleep(1)
            self.round_time -= 1

            if self.round_time <= 0:
                await self.skip_round(True)

    async def round_start(self):
        tmp = f'or get {self.cards_to_take} cards' if self.cards_to_take > 0 else ''

        current_player_embed = discord.Embed(title="It's your turn",
                                             description=f"pick a card {tmp}",
                                             color=0x00ff00)
        current_player_embed.add_field(name="Current Card",
                                       value=self.played_deck[0].get_user_friendly(),
                                       inline=False)
        current_player_embed.add_field(name="Your Deck",
                                       value=await self.list_deck(self.deck(self.current_player)),
                                       inline=False)

        other_players_embed = discord.Embed(title=f"It's {self.current_player.display_name}'s Turn",
                                            description="They're Picking A Card", color=0x00ff00)

        await self.excluding(self.current_player).send(embed=other_players_embed)
        await self.current_player.send(embed=current_player_embed)

        self.state = State.CARD_PICK
        self.round_time = 20

    async def player_leave(self, player):
        if player.id == self.current_player.id:
            await self.skip_round(True)
        await super(UnoGame, self).player_leave(player)

    async def skip_round(self, forced):
        """prematurely ends the round
        it gives the player the required amount of cards"""

        defined_amount = self.cards_to_take > 0
        cards_taken = 0
        if self.state == State.FILL_ATTRIBUTES:
            self.played_deck.append(self.selected_card)
            await self.played_deck[0].force_place(self)
            await self.excluding(self.current_player).send(
                f"{self.current_player.mention} plays {self.selected_card.get_user_friendly()}")
            await self.current_player.send(f"you play {self.selected_card.get_user_friendly()}")
            return

        while True:
            card = self.global_deck.pop()
            cards_taken = cards_taken + 1

            if defined_amount:
                self.deck(self.current_player).append(card)
                if cards_taken >= self.cards_to_take:
                    await self.current_player.send(f"You get {self.cards_to_take} card"
                                                   f"{'' if self.cards_to_take == 1 else 's'}")
                    await self.excluding(self.current_player).send(f"{self.current_player.mention} get "
                                                                   f"{self.cards_to_take} card"
                                                                   f"{'' if self.cards_to_take == 1 else 's'}")
                    self.cards_to_take = 0
                    await self.end_round()
                    return
            else:
                allowed = await self.played_deck[0].other_place_attempt(card, self)
                if allowed:
                    if forced:
                        self.played_deck.append(card)
                        await self.played_deck[0].force_place(self)
                        await self.current_player.send(f"You get {cards_taken} card"
                                                       f"{'' if self.cards_to_take == 1 else 's'} and play "
                                                       f"{self.played_deck[0].get_user_friendly()}")
                        await self.excluding(self.current_player).send(f"{self.current_player.mention} gets"
                                                                       f" {cards_taken} card"
                                                                       f"{'' if self.cards_to_take == 1 else 's'} and "
                                                                       f"plays "
                                                                       f"{self.played_deck[0].get_user_friendly()}")
                        await self.end_round()
                    else:
                        await self.current_player.send(f"You get {cards_taken} card"
                                                       f"{'' if self.cards_to_take == 1 else 's'} and use "
                                                       f"{card.get_user_friendly()}")
                        await self.excluding(self.current_player).send(f"{self.current_player.mention} gets"
                                                                       f" {cards_taken} card"
                                                                       f"{'' if self.cards_to_take == 1 else 's'}")
                        await self.begin_attribute_filling(card)
                    return
                else:
                    self.deck(self.current_player).append(card)

    async def end_round(self):
        """called when a round ends"""
        if len(self.deck(self.current_player)) == 0:
            await self.end_game(EndGame.WIN, self.current_player)
        else:
            self.cycle_round()
            await self.round_start()

    async def on_message(self, message):
        if message.author.id == self.current_player.id:
            # the message is from current player

            try:
                selection = int(message.content)
            except ValueError:
                if message.content == "skip":
                    await self.skip_round(False)
            else:
                if 0 <= selection < len(self.deck(self.current_player)):
                    selected_card = self.deck(self.current_player)[selection]

                    allowed = await self.played_deck[0].other_place_attempt(selected_card, self)

                    if allowed:
                        self.round_time += 5
                        self.deck(self.current_player).pop(selection)
                        await self.begin_attribute_filling(selected_card)
                    else:
                        await self.current_player.send("You can't play that card")
                else:
                    await self.current_player.send("You picked an invalid card")

    async def begin_attribute_filling(self, card):
        """start filling the attributes for a card, or plays the card if there's no attributes"""
        self.selected_card = card
        self.attributes = {}
        self.requested_attributes = await card.required_attributes()
        if len(self.requested_attributes) > 0:
            self.state = State.FILL_ATTRIBUTES

            await self.next_attribute_filling()
        else:
            await self.play_card()

    async def next_attribute_filling(self):
        """prepares everything for an attribute to be filled it"""
        self.filling_attribute = list(self.requested_attributes.keys())[0]
        self.attribute_request_type = self.requested_attributes[self.filling_attribute]
        del self.requested_attributes[self.filling_attribute]

        if self.attribute_request_type is Color:
            embed = discord.Embed(title="Pick a color", description="", color=0x00ff00)

            self.bound_message = await self.current_player.send(embed=embed)

            for emoji in emoji_to_color:
                await self.bound_message.add_reaction(emoji)

    async def fill_attribute(self, value):
        """gets a value and fills in the attribute, and prepares next attribute"""
        self.round_time += 5
        self.attributes[self.filling_attribute] = value
        if len(self.requested_attributes) > 0:
            await self.next_attribute_filling()
        else:
            await self.play_card()

    async def on_reaction_add(self, reaction, user):
        if self.attribute_request_type is Color:
            if reaction.message.id == self.bound_message.id and \
                    user.id == self.current_player.id:
                await self.fill_attribute(emoji_to_color[reaction.emoji])

    async def play_card(self):
        """plays the selected card and ends the round"""
        self.played_deck.insert(0, self.selected_card)
        await self.selected_card.place(self, self.attributes)

        await self.excluding(self.current_player).send(
            f"{self.current_player.mention} plays {self.selected_card.get_user_friendly()}")
        await self.current_player.send(f"you play {self.selected_card.get_user_friendly()}")

        await self.end_round()

    def deck(self, player):
        return self.players_decks[player.id]

    @property
    def current_player(self):
        return self.players[self.current_player_idx]

    async def list_deck(self, deck):
        ret = []
        for idx, card in enumerate(deck):
            if await self.played_deck[0].other_place_attempt(card, self):
                ret.append(f"__`{idx}: `__{card.get_user_friendly()}")
            else:
                ret.append(f"`{idx}: `{card.get_user_friendly()}")
        return "\n".join(ret)

    def cycle_round(self):
        self.current_player_idx += 1 if self.direction == registry.Direction.UP_WARDS else -1
        self.current_player_idx = (self.current_player_idx + len(self.players)) % len(self.players)
