import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import List

import discord
from discord import Member, TextChannel, User

from games.MulticastIntent import MulticastIntent


class EndGame(Enum):
    DRAW = 0
    WIN = 1
    INSUFFICIENT_PLAYERS = 2
    ERROR = 3


class Game(ABC, MulticastIntent):
    def __init__(self, cog, channel: TextChannel, players: List[User]):
        super().__init__(players)
        self.channel = channel
        self.running = True
        self.cog = cog
        self.players = players
        self.lock = asyncio.Lock()

    async def end_game(self, code: EndGame, *args):
        if code == EndGame.DRAW:
            embed = discord.Embed(title="Game",
                                  description=f"Draw",
                                  color=0xffff00)
        elif code == EndGame.WIN:
            embed = discord.Embed(title="Game",
                                  description=f"{args[0].mention} won",
                                  color=0x00ff00)
        elif code == EndGame.INSUFFICIENT_PLAYERS:
            embed = discord.Embed(title="Game",
                                  description=f"The game ended because everyone ran away",
                                  color=0xaaaaaa)
        elif code == EndGame.ERROR:
            embed = discord.Embed(title="Game",
                                  description=f"The game ended because applejuice is an idiot and let a crash slip"
                                              f" by\n{str(args[0])}",
                                  color=0xaa4444)
        else:
            embed = discord.Embed(title="Game",
                                  description=f"The game ended",
                                  color=0x333333)

        await self.including(self.channel).send(embed=embed)
        self.cog.game_instances.remove(self)
        self.running = False
        for player in self.players:
            del self.cog.user_state[player.id]

    async def on_start(self):
        pass

    async def on_message(self, message):
        pass
    
    async def is_still_playable(self):
        return len(self.players) > 1

    async def player_leave(self, player):
        embed = discord.Embed(title="Game",
                              description=f"{player.mention} left",
                              color=0x333333)

        await self.send(embed=embed)

        self.players.remove(player)
        del self.cog.user_state[player.id]

        if not self.is_still_playable():
            await self.end_game(EndGame.INSUFFICIENT_PLAYERS)

    @property
    def bot(self):
        return self.cog.bot
