import base64
import math
import random

import aiohttp
import nextcord

from games.Game import EndGame
from games.GameHasTimeout import GameWithTimeout
from games.GamePlayer import GamePlayer
from games.GameSetting import GameSetting


def decode_data(data):
    data = data.copy()
    if isinstance(data, dict):
        for key in data:
            if isinstance(data[key], str):
                data[key] = base64.b64decode(data[key]).decode()
            else:
                data[key] = decode_data(data[key])
    else:
        for idx in range(len(data)):
            if isinstance(data[idx], str):
                data[idx] = base64.b64decode(data[idx]).decode()
            else:
                data[idx] = decode_data(data[idx])
    return data


def bar(size, value, letter):
    return "|" + (" " * math.floor(value * size)) + letter + (" " * math.ceil((1 - value) * size)) + ":"


class TriviaGamePlayer(GamePlayer):
    def __init__(self, user, bound_channel):
        super().__init__(user, bound_channel)
        self.response = None
        self.points = 0


class TriviaGame(GameWithTimeout):
    game_name = "trivia"
    game_specific_settings = {
        "initial_barrier_span": GameSetting("The initial barrier span", int, 10, lambda new_val: new_val > 3),
        "span_decrease_for_round": GameSetting("How much the barrier span decreases each round", float, 0.5),
        "answer_multiplier": GameSetting("How much should the final answer points be multiplied", float, 1,
                                         lambda new_val: new_val != 0)
    }
    game_player_class = TriviaGamePlayer

    def __init__(self, cog, channel, players, settings):
        super().__init__(cog, channel, players, settings)
        self.trivia_token = None
        self.trivia_question = None

        self.answers = None
        self.correct_answer_idx = None
        self.embed = None

        self.barrier_span = self.settings["initial_barrier_span"]
        self.barrier = 0

        for player in self.players:
            player.points = self.settings["initial_barrier_span"]

    async def fetch_question(self):
        async with aiohttp.request("GET", f"https://opentdb.com/api.php?amount=1"
                                          f"&token={self.trivia_token}&encode=base64") as response:
            self.trivia_question = decode_data((await response.json())["results"][0])

    async def on_start(self):
        await super(TriviaGame, self).on_start()
        async with aiohttp.request("GET", "https://opentdb.com/api_token.php?command=request") as response:
            self.trivia_token = (await response.json())["token"]

        await self.start_round()

    async def on_message(self, message, player):
        if self.trivia_question["type"] == "boolean":
            content = message.content
            player.response = content.lower() in ("y", "yes", "true", "1", "on", "ye", "true")
        else:
            try:
                value = int(message.content)
            except ValueError:
                pass
            else:
                player.response = value

    async def close_round(self):
        skew = 0
        if self.trivia_question["difficulty"] == "medium":
            skew = 0.2
        elif self.trivia_question["difficulty"] == "hard":
            skew = 0.4

        max_points = -math.inf

        got_wrongs = []

        for player in self.players:
            response = player.response

            if self.trivia_question["type"] == "boolean":
                correct = response == (self.trivia_question["correct_answer"] == "True")
            else:
                correct = response == self.correct_answer_idx

            if correct:
                points = (1 + skew) * self.settings["answer_multiplier"]
                player.points += points
                await player.send(f"Correct answer (+{points} points)")
            else:
                points = (1 - skew) * 0.9 * self.settings["answer_multiplier"]
                player.points -= points
                got_wrongs.append(player)
                await player.send(f"Incorrect answer (-{round(points, 3)} points)")
            player.points = round(player.points, 3)
            max_points = max(max_points, player.points)

        self.barrier = round(max(self.barrier, max_points - self.barrier_span), 3)

        frag = []
        lost = []

        for player in self.players:
            points = player.points
            warning = ""
            if self.barrier > points:
                warning = "(claimed by the barrier)"
                lost.append(player)
            elif self.barrier + 2 > points:
                warning = "(nearing the barrier)"
            frag.append(f"{player.mention}: {points} points {'📉' if player in got_wrongs else '📈'} {warning}")

        frag.append(f"Barrier: {self.barrier} points")

        embed = nextcord.Embed(title="Results",
                               description="\n".join(frag),
                               color=0xaaaaaa)

        frag = ["```"]
        for player in self.players:
            points = player.points

            if points > self.barrier:
                frag.append(bar(math.ceil((self.barrier_span / self.settings["initial_barrier_span"]) * 40),
                                (points - self.barrier) / self.barrier_span,
                                player.name[0]))

        frag.append("|")
        frag.append("barrier")
        frag.append("```")

        embed.add_field(name="Field", value="\n".join(frag))

        await self.players.send(embed=embed)

        if len(lost) > 0:
            if len(lost) == len(self.players):
                await self.end_game(EndGame.DRAW)
                return
            else:
                for player in lost:
                    await self.player_leave(player, "They got claimed by the barrier")

                if len(self.players) == 1:
                    await self.end_game(EndGame.WIN, self.players[0])
                    return

        self.barrier_span -= self.settings["span_decrease_for_round"]
        self.after(5, self.start_round())

    async def timeout(self):
        await self.close_round()

    async def start_round(self):
        for player in self.players:
            player.response = None
        await self.fetch_question()
        self.process_question()
        await self.players.send(embed=self.embed)
        self.reset_timer()

    def process_question(self):
        color = 0x44aa44
        if self.trivia_question["difficulty"] == "medium":
            color = 0x777744
        elif self.trivia_question["difficulty"] == "hard":
            color = 0xaa4444

        self.embed = nextcord.Embed(title=f"{self.trivia_question['category']}: {self.trivia_question['difficulty']}",
                                    description=self.trivia_question["question"],
                                    color=color)

        if self.trivia_question["type"] == "boolean":
            self.embed.add_field(name="Is this true or false?", value="\u200C")
        else:
            self.answers = self.trivia_question["incorrect_answers"].copy()
            random.shuffle(self.answers)

            self.correct_answer_idx = random.randrange(0, len(self.answers))
            self.answers.insert(self.correct_answer_idx, self.trivia_question["correct_answer"])

            self.embed.add_field(name="send the index of the correct answer:", value="\n"
                                 .join(f"{idx}: {answer}" for idx, answer in enumerate(self.answers)))

    @classmethod
    def is_playable(cls, size):
        return size > 0
