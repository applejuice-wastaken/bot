from abc import abstractmethod
from enum import Enum
from typing import List, Sequence

from games.Game import EndGame, LeaveReason
from games.GameHasTimeout import GameWithTimeout
from games.round.RoundAction import RoundAction, Category, Verb, Literal
from etcetra.human_join_list import human_join_list


def action_join(actions: Sequence[Sequence[Category]]):
    groupings = []
    current_group = None
    current_format = None

    for action in actions:
        action_format = []

        for particle in action:
            if isinstance(particle, Verb):
                action_format.append(Verb)
            else:
                action_format.append(particle.content)

        if action_format != current_format:
            current_group = []
            groupings.append(current_group)
            current_format = action_format

        current_group.append(action)

    ret = []

    for group in groupings:
        ret.append(equal_action_join(group))

    return human_join_list(ret, analyse_contents=True)


def equal_action_join(actions: Sequence[Sequence[Category]]):
    def default():
        return human_join_list([" ".join(p.content for p in a) for a in actions])

    expected_length = len(actions[0])
    ret = []

    for output in actions:
        if len(output) != expected_length:
            return default()

    for idx in range(expected_length):
        expected_type = type(actions[0][idx])

        composition = []

        for action in actions:
            particle = action[idx]

            if type(particle) is not expected_type:
                return default()

            if expected_type is Verb:
                composition.append(particle.content)

            elif expected_type is Literal:
                if particle.content != actions[0][idx].content:
                    return default()

            else:
                return default()

        if expected_type is Verb:
            final = human_join_list(composition)

        elif expected_type is Literal:
            final = actions[0][idx].content

        else:
            return default()

        ret.append(final)

    return " ".join(ret)


class RoundGame(GameWithTimeout):
    def __init__(self, cog, channel, players, settings):
        super().__init__(cog, channel, players, settings)
        self.current_player_idx = 0
        self.next_player_idx = 0
        self.direction = Direction.DOWN_WARDS

        self.queued_round_actions: List[RoundAction] = []

    async def on_start(self):
        await super(RoundGame, self).on_start()
        self.after(1, self.begin_round())

    @abstractmethod
    async def begin_round(self):
        pass

    @abstractmethod
    async def timeout_round(self):
        pass

    async def timeout(self):
        await self.timeout_round()

    @abstractmethod
    def is_win(self):
        pass

    async def player_leave(self, player, reason=LeaveReason.BY_COMMAND):
        if self.current_player.id == player.id:
            await self.end_round()

        if self.current_player_idx > self.players.index(player):
            self.current_player_idx -= 1

        await super(RoundGame, self).player_leave(player, reason)

    async def end_round(self):
        await self.update_round_actions()
        if self.is_win():
            await self.end_game(EndGame.WIN, self.current_player)
        else:
            self.cycle()
            self.current_player_idx = self.next_player_idx
            await self.begin_round()
            self.reset_timer()

    def add_round_action(self, action):
        self.queued_round_actions.append(action)

    async def update_round_actions(self):
        for player in self.players:
            await player.send(self.compose_round_actions(self.queued_round_actions, player))

        self.queued_round_actions.clear()

    def compose_round_actions(self, list_of_actions, for_player) -> str:
        chunk = []
        about_player = None
        same_player_chunks = []

        for action in list_of_actions:
            author = action.get_author()

            if author != about_player:
                if len(chunk) > 0:

                    same_player_chunk = ""

                    if about_player is not None:
                        # if the action is tied to someone, we should reference the author
                        same_player_chunk += "you " if for_player == about_player else (about_player.mention + " ")

                    same_player_chunk += action_join(chunk)
                    same_player_chunks.append(same_player_chunk)
                    chunk.clear()

                about_player = author

            chunk.append(action.represent(for_player == author))

        if len(chunk) > 0:

            same_player_chunk = ""

            if about_player is not None:
                same_player_chunk += "You " if for_player == about_player else (about_player.mention + " ")

            same_player_chunk += action_join(chunk)

            same_player_chunks.append(same_player_chunk)

        return human_join_list(same_player_chunks, analyse_contents=True)

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
