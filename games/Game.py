import abc
import asyncio
from contextlib import suppress
from enum import Enum
from functools import partial
from typing import Dict, Union

import nextcord
from nextcord import TextChannel

from games.GamePlayer import GamePlayer
from games.GameSetting import GameSetting
from games.MulticastIntent import AbstractMulticastIntent


class EndGame(Enum):
    DRAW = 0
    WIN = 1
    INSUFFICIENT_PLAYERS = 2
    ERROR = 3


class LeaveReason(Enum):
    CHANNEL_BLOCKED = 0
    BY_COMMAND = 1


class PlayerList(AbstractMulticastIntent, list):
    def get_targets(self):
        return self


class Game(abc.ABC):
    game_name = "game"
    game_specific_settings: Dict[str, GameSetting] = {}
    game_player_class = GamePlayer

    def __init__(self, cog, channel: TextChannel, players, settings):
        self.channel = channel
        self.running = True
        self.cog = cog
        self.players = PlayerList(players)
        self.lock = asyncio.Lock()
        self.settings = settings

    @classmethod
    def calculate_game_settings(cls):
        ret = {}

        for mro_cls in cls.mro()[::-1]:
            if hasattr(mro_cls, "game_specific_settings") and "game_specific_settings" in vars(mro_cls):
                ret.update(mro_cls.game_specific_settings)

        return ret

    async def end_game(self, code: EndGame, *args):
        if code == EndGame.DRAW:
            embed = nextcord.Embed(title="Game",
                                   description=f"Draw",
                                   color=0xffff00)
        elif code == EndGame.WIN:
            embed = nextcord.Embed(title="Game",
                                   description=f"{args[0].mention} won",
                                   color=0x00ff00)
        elif code == EndGame.INSUFFICIENT_PLAYERS:
            embed = nextcord.Embed(title="Game",
                                   description=f"The game ended because everyone ran away",
                                   color=0xaaaaaa)
        elif code == EndGame.ERROR:
            embed = nextcord.Embed(title="Game",
                                   description=f"The game ended because applejuice is an idiot and let a crash slip"
                                               f" by\n{str(args[0])}",
                                   color=0xaa4444)
        else:
            embed = nextcord.Embed(title="Game",
                                   description=f"The game ended",
                                   color=0x333333)

        await self.players.including(self.channel).send(embed=embed)
        self.cog.game_instances.remove(self)
        self.running = False
        for player in self.players:
            del self.cog.user_state[player.id]
        raise GameEndedException

    async def on_start(self):
        pass

    async def on_message(self, message, player):
        pass

    async def on_reaction_add(self, reaction, player):
        pass

    @classmethod
    def is_playable(cls, size):
        return size > 1

    def is_still_playable(self):
        return self.is_playable(len(self.players))

    async def player_leave(self, player, reason: Union[LeaveReason, str] = LeaveReason.BY_COMMAND):
        if isinstance(reason, str):
            text = reason
        elif reason == LeaveReason.BY_COMMAND:
            text = "the leave command was triggered"
        elif reason == LeaveReason.CHANNEL_BLOCKED:
            text = "they left because I could no longer send messages to their bound channel"
        else:
            text = ""

        embed = nextcord.Embed(title="Game",
                               description=f"{player.mention} left\n{text}",
                               color=0x333333)

        await self.players.send(embed=embed)

        self.players.remove(player)
        del self.cog.user_state[player.id]

        if not self.is_still_playable():
            await self.end_game(EndGame.INSUFFICIENT_PLAYERS)

    @property
    def bot(self):
        return self.cog.bot

    def player_from_id(self, id_):
        for player in self.players:
            if player.id == id_:
                return player

    def after(self, seconds, callback):
        loop = asyncio.get_running_loop()
        return loop.call_later(seconds, partial(asyncio.ensure_future, self.call_wrap(callback), loop=loop))

    async def call_wrap(self, coroutine):
        async with self.lock:
            if self.running:
                try:
                    with suppress(GameEndedException):
                        await coroutine

                    to_leave = []

                    for player in self.players:
                        if not player.able_to_send_messages:
                            to_leave.append(player)

                    for player in to_leave:
                        await self.player_leave(player, LeaveReason.CHANNEL_BLOCKED)

                except Exception as e:
                    with suppress(GameEndedException):
                        await self.end_game(EndGame.ERROR, e)
                    raise

            else:
                coroutine.close()


class GameEndedException(Exception):
    pass
