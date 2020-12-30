from abc import abstractmethod

from games.Game import Game

class RoundGame(Game):
    def __init__(self, cog, channel, players):
        super().__init__(cog, channel, players)
        self.timeout = None

    async def on_start(self):
        self.timeout = 20

    @abstractmethod
    async def begin_round(self):
        pass

    @abstractmethod
    async def end_round(self):
        pass

    @abstractmethod
    async def skip_round(self, from_timeout: bool):
        await self.end_round()
