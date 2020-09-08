import asyncio
import time
from enum import Enum

import discord

from games.Game import Game
from games.uno import registry


class UnoGame(Game):
    def __init__(self, bot, guild, players):
        super().__init__(bot, guild, players)
        self.current_player_idx = 0
        self.direction = registry.Direction.UP_WARDS
        self.timeout = 10
        self.players_decks = {}
        self.global_deck = registry.generate_deck()
        self.played_deck = []
        self.cards_to_take = 0

    async def player_leave(self, player):
        if self.current_player != player:
            del self.players_decks[player.id]
            idx = self.players.index(player)
            if idx < self.current_player_idx:
                self.current_player_idx -= 1

            embed = discord.Embed(title="Leaving", description=f"{player.display_name} Left",
                                  color=0xff0000)
            for player in self.players:
                await player.send(embed=embed)

            return await super(UnoGame, self).player_leave(player)
        else:
            await player.send("You can't leave on your turn")
            return False

    @property
    def current_player(self):
        return self.players[self.current_player_idx]

    async def run(self):
        for player in self.players:
            self.players_decks[player.id] = []
            for i in range(7):
                self.players_decks[player.id].append(self.global_deck.pop())

        self.played_deck.append(self.global_deck.pop())
        await self.played_deck[0].cls.force_place(self.played_deck[0], self)

        while True:
            self.timeout = 15

            res = await self.round_logic()

            if res == 0:
                pass
            elif res == -1:
                done = False
                c = 0
                player_deck = self.players_decks[self.current_player.id]
                while not done:
                    new_card = self.global_deck.pop()
                    allowed = await self.played_deck[0].cls.other_place_attempt(self.played_deck[0], new_card, self)
                    if allowed:
                        await new_card.cls.force_place(new_card, self)
                        self.played_deck.insert(0, new_card)
                        await self.current_player.send(f"You get {c + 1} cards and play a"
                                                       f" {new_card.cls.get_user_friendly(new_card)}")
                        done = True
                    else:
                        player_deck.append(new_card)
                    c += 1
            else:

                player_deck = self.players_decks[self.current_player.id]
                for i in range(res):
                    new_card = self.global_deck.pop()
                    player_deck.append(new_card)

                self.cards_to_take = 0
                await self.current_player.send(f"You get {res} cards")

            for player in self.players:
                if len(self.players_decks[player.id]) == 0:
                    embed = discord.Embed(title="Winner", description=f"{self.current_player.display_name} Won",
                                          color=0x00ff00)

                    for player in self.players:
                        await player.send(embed=embed)
                    return

            self.make_round()

    async def round_logic(self):
        player_deck = self.players_decks[self.current_player.id]

        tmp = f'Or Get {self.cards_to_take} Cards' if self.cards_to_take > 0 else ''

        current_player_embed = discord.Embed(title="It's your turn",
                                             description=f"Pick A Card {tmp}",
                                             color=0x00ff00)
        current_player_embed.add_field(name="Current Card",
                                       value=self.played_deck[0].cls.get_user_friendly(self.played_deck[0]),
                                       inline=False)
        current_player_embed.add_field(name="Your Deck",
                                       value=await self.list_deck(player_deck),
                                       inline=False)

        other_players_embed = discord.Embed(title=f"It's {self.current_player.display_name}'s Turn",
                                            description="They're Picking A Card", color=0x00ff00)

        await self.current_player.send(embed=current_player_embed)
        for player in self.players:
            if player != self.current_player:
                await player.send(embed=other_players_embed)

        picked = None

        while picked is None:  # pick card
            await self.current_player.send(f"Send the number of the card you wish to play with, or 'skip' to skip,"
                                           f" you have {self.timeout} seconds")

            def initial_pick_check(m):
                try:
                    p = int(m.content)
                except ValueError:
                    return m.content == "skip"
                else:
                    return p >= 0 or p > len(player_deck)

            before_send = time.time()
            try:
                message = await self.bot.wait_for('message', timeout=self.timeout, check=initial_pick_check)
            except asyncio.TimeoutError:
                return -1 if self.cards_to_take == 0 else self.cards_to_take

            if message.content == "skip":
                return -1 if self.cards_to_take == 0 else self.cards_to_take

            time_took = time.time() - before_send

            self.timeout -= time_took

            allowed = await self.played_deck[0].cls.other_place_attempt(self.played_deck[0],
                                                                        player_deck[int(message.content)], self)

            if allowed:
                picked = int(message.content)
            else:
                await self.current_player.send("You can't pick this card!")

        await player_deck[picked].cls.place(player_deck[picked], self)

        if self.timeout == 0:
            return -1 if self.cards_to_take == 0 else self.cards_to_take

        picked_card = player_deck.pop(picked)

        self.played_deck.insert(0, picked_card)

        return 0

    async def list_deck(self, deck):
        ret = []
        for idx, card in enumerate(deck):
            if await self.played_deck[0].cls.other_place_attempt(self.played_deck[0], card, self):
                ret.append(f"**`{idx}: `**{card.cls.get_user_friendly(card)}")
            else:
                ret.append(f"`{idx}: `{card.cls.get_user_friendly(card)}")
        return "\n".join(ret)

    def make_round(self):
        self.current_player_idx += 1 if self.direction == registry.Direction.UP_WARDS else -1
        self.current_player_idx = (self.current_player_idx + len(self.players)) % len(self.players)
