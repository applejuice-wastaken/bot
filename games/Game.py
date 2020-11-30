from abc import ABC, abstractmethod
from enum import Enum

import discord

from games.MulticastIntent import MulticastIntent


class EndGame(Enum):
    DRAW = 0
    WIN = 1
    INSUFFICIENT_PLAYERS = 2


class Game(ABC, MulticastIntent):
    def __init__(self, cog, channel, players):
        super().__init__(players)
        self.channel = channel
        self.running = True
        self.cog = cog
        self.players = players

    async def end_game(self, code: EndGame, who: discord.User):
        if code == EndGame.DRAW:
            embed = discord.Embed(title="Game",
                                  description=f"Draw",
                                  color=0xffff00)
        elif code == EndGame.WIN:
            embed = discord.Embed(title="Game",
                                  description=f"{who.mention} won",
                                  color=0x00ff00)
        elif code == EndGame.INSUFFICIENT_PLAYERS:
            embed = discord.Embed(title="Game",
                                  description=f"The game ended because everyone ran away",
                                  color=0xaaaaaa)
        else:
            embed = discord.Embed(title="Game",
                                  description=f"The game ended",
                                  color=0x333333)

        await self.channel.send(embed=embed)
        self.cog.game_instances.remove(self)
        self.running = False

    async def on_start(self):
        pass

    async def player_leave(self, player):
        self.players.remove(player)
        del self.cog.user_state[player.id]

    @property
    def bot(self):
        return self.cog.bot
