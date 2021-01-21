import asyncio
from abc import ABC, abstractmethod
from functools import partial

from games.Game import Game
from games.GameSetting import GameSetting


class GameWithTimeout(Game, ABC):
    game_specific_settings = {"timeout": GameSetting("Timeout", int, 20, lambda new_val: new_val > 0)}

    def __init__(self, cog, channel, players, settings):
        super().__init__(cog, channel, players, settings)
        self.round_timeout = None

    async def decrement(self):
        while self.running:
            await asyncio.sleep(1)
            self.round_timeout -= 1

            if self.round_timeout == 0:
                await self.call_wrap(self.timeout())

    async def on_start(self):
        self.reset_timer()
        loop = asyncio.get_running_loop()
        loop.call_soon(partial(asyncio.ensure_future, self.decrement(), loop=loop))

    @abstractmethod
    async def timeout(self):
        raise NotImplementedError

    def reset_timer(self):
        self.round_timeout = self.settings["timeout"]
