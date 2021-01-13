import asyncio
import base64
import math

import aiohttp
import discord
import random

from games.Game import Game, EndGame
from util.LineConstructor import LineConstructor


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

def human_join_list(input_list: list):
    if len(input_list) == 0:
        return ""
    elif len(input_list) == 1:
        return input_list[0]
    else:
        return " and ".join((", ".join(input_list[:-1]), input_list[-1]))


class TriviaGame(Game):
    def __init__(self, cog, channel, players):
        super().__init__(cog, channel, players)
        self.trivia_token = None
        self.trivia_question = None

        self.answers = None
        self.correct_answer_idx = None
        self.embed = None

        self.barrier_span = 10
        self.barrier = 0

        self.player_responses = {}
        self.player_points = {}

    async def fetch_question(self):
        async with aiohttp.request("GET", f"https://opentdb.com/api.php?amount=1"
                                          f"&token={self.trivia_token}&encode=base64") as response:
            self.trivia_question = decode_data((await response.json())["results"][0])

    async def on_start(self):
        async with aiohttp.request("GET", "https://opentdb.com/api_token.php?command=request") as response:
            self.trivia_token = (await response.json())["token"]

        for player in self.players:
            self.player_points[player.id] = 10

        await self.start_round()

    async def on_message(self, message):
        try:
            value = int(message.content)
        except ValueError:
            pass
        else:
            self.player_responses[message.author.id] = value

    async def close_round(self):
        skew = 0
        if self.trivia_question["difficulty"] == "medium":
            skew = 0.2
        elif self.trivia_question["difficulty"] == "hard":
            skew = 0.4

        max_points = -math.inf

        for player_id in self.player_responses:
            response = self.player_responses[player_id]
            if response == self.correct_answer_idx:
                self.player_points[player_id] += 1 + skew
                await self.player_from_id(player_id).send(f"Correct answer (+{1 + skew} points)")
            else:
                self.player_points[player_id] -= 1 - skew
                await self.player_from_id(player_id).send(f"Incorrect answer (-{1 - skew} points)")
            self.player_points[player_id] = round(self.player_points[player_id], 1)
            max_points = max(max_points, self.player_points[player_id])

        self.barrier = round(max(self.barrier, max_points - self.barrier_span), 1)

        frag = []
        lost = []

        for player in self.players:
            points = self.player_points[player.id]
            warning = ""
            if self.barrier > points:
                warning = "(claimed by the barrier)"
                lost.append(player)
            elif self.barrier + 2 > points:
                warning = "(nearing the barrier)"
            frag.append(f"{player.mention}: {points} points {warning}")

        frag.append(f"Barrier: {self.barrier} points")

        embed = discord.Embed(title="Results",
                              description="\n".join(frag),
                              color=0xaaaaaa)

        frag = ["```"]
        for player in self.players:
            points = self.player_points[player.id]

            letter_position = int((points - self.barrier) * 3)

            if letter_position > 0:
                constructor = LineConstructor(math.ceil(self.barrier_span * 3))

                constructor.set(letter_position, player.name[0])
                constructor.set(0, "|")
                constructor.set(int(self.barrier_span * 3) - 1, ":")

                frag.append(constructor.get())

        frag.append("|")
        frag.append("barrier")
        frag.append("```")

        embed.add_field(name="Field", value="\n".join(frag))

        await self.send(embed=embed)

        if len(lost) > 0:
            if len(lost) == len(self.players):
                await self.end_game(EndGame.DRAW)
                return
            else:
                for player in lost:
                    await self.player_leave(player)

                if len(self.players) == 1:
                    await self.end_game(EndGame.WIN, self.players[0])
                    return

        self.barrier_span -= 0.1
        self.after(5, self.start_round())

    def is_still_playable(self):
        return True

    async def start_round(self):
        for player in self.players:
            self.player_responses[player.id] = None
        await self.fetch_question()
        self.process_question()
        await self.send(embed=self.embed)
        self.after(30, self.close_round())

    def process_question(self):
        color = 0x44aa44
        if self.trivia_question["difficulty"] == "medium":
            color = 0x777744
        elif self.trivia_question["difficulty"] == "hard":
            color = 0xaa4444

        self.embed = discord.Embed(title=f"{self.trivia_question['category']}: {self.trivia_question['difficulty']}",
                                   description=self.trivia_question["question"],
                                   color=color)

        self.answers = self.trivia_question["incorrect_answers"].copy()
        random.shuffle(self.answers)

        self.correct_answer_idx = random.randrange(0, len(self.answers))
        self.answers.insert(self.correct_answer_idx, self.trivia_question["correct_answer"])

        self.embed.add_field(name="send the index of the correct answer:", value="\n"
                             .join(f"{idx}: {answer}" for idx, answer in enumerate(self.answers)))
