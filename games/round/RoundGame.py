import asyncio
from abc import abstractmethod
from enum import Enum
from functools import partial
from games.Game import Game, EndGame


def human_join_list(input_list: list):
    if len(input_list) == 0:
        return ""
    elif len(input_list) == 1:
        return input_list[0]
    else:
        return " and ".join((", ".join(input_list[:-1]), input_list[-1]))


class RoundGame(Game):
    def __init__(self, cog, channel, players, settings):
        super().__init__(cog, channel, players, settings)
        self.round_timeout = None
        self.current_player_idx = 0
        self.next_player_idx = 0
        self.direction = Direction.DOWN_WARDS

        self.queued_round_actions = []
        self.total_round_actions = []

    async def decrement(self):
        while self.running:
            await asyncio.sleep(1)
            self.round_timeout -= 1

            if self.round_timeout == 0:
                await self.call_wrap(self.timeout_round())

    async def on_start(self):
        self.round_timeout = 20

        loop = asyncio.get_running_loop()

        self.after(1, self.begin_round())
        loop.call_soon(partial(asyncio.ensure_future, self.decrement(), loop=loop))

    @abstractmethod
    async def begin_round(self):
        pass

    @abstractmethod
    async def timeout_round(self):
        pass

    @abstractmethod
    def is_win(self):
        pass

    async def player_leave(self, player):
        if self.current_player.id == player.id:
            await self.end_round()

        if self.current_player_idx > self.players.index(player):
            self.current_player_idx -= 1

        await super(RoundGame, self).player_leave(player)

    async def end_round(self):
        await self.update_round_actions()
        if self.is_win():
            await self.end_game(EndGame.WIN, self.current_player)
        else:
            self.cycle()
            self.current_player_idx = self.next_player_idx
            await self.begin_round()
            self.round_timeout = 20

    def add_round_action(self, action):
        self.queued_round_actions.append(action)

    async def update_round_actions(self):
        for player in self.players:
            await player.send(self.compose_round_actions(self.queued_round_actions, player))

        self.queued_round_actions.clear()

    def compose_round_actions(self, list_of_actions, for_user) -> str:
        chunks = []
        for action in list_of_actions:
            chunks.append(action.represent(for_user == self.current_player))

        return ("You " if self.current_player == for_user else (self.current_player.mention + " ")) + \
            human_join_list(chunks)

    def cycle(self):
        if self.direction == Direction.UP_WARDS:
            self.next_player_idx -= 1
        else:
            self.next_player_idx += 1
        self.next_player_idx = (self.next_player_idx + len(self.players)) % len(self.players)

    @property
    def current_player(self):
        return self.players[self.current_player_idx]


class Direction(Enum):
    UP_WARDS = 1
    DOWN_WARDS = 2
