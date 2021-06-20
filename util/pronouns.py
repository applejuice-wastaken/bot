import random
import typing
from dataclasses import dataclass
import dataclasses
from json.decoder import JSONDecodeError

import aiohttp
import discord


@dataclass(frozen=True, eq=True)
class Pronoun:
    pronoun_subject: str
    pronoun_object: str
    possessive_determiner: str
    possessive_pronoun: str
    reflexive: str


cache = {}

to_fill = [
    Pronoun("he", "him", "his", "his", "himself"),
    Pronoun("she", "her", "her", "hers", "herself"),
    Pronoun("they", "them", "their", "theirs", "themselves")
           ]

for pronoun_to_fill in to_fill:
    for morpheme in dataclasses.astuple(pronoun_to_fill):
        cache[morpheme] = pronoun_to_fill

default = cache["they"]

async def figure_pronouns(member: discord.Member) -> typing.Optional[Pronoun]:
    if isinstance(member, discord.User) or member.discriminator == "0000":
        return await fetch_pronoun("them")

    available = []

    for role in member.roles:
        role: discord.Role

        if "/" in role.name:
            chunks = role.name.split("/")

            pronoun = None

            if len(chunks) == 5:
                pronoun = Pronoun(*chunks)

            else:
                for chunk in chunks:
                    pronoun = await fetch_pronoun(chunk)

                    if pronoun is not None:
                        break

            if pronoun is not None:
                available.append(pronoun)

        elif role.name == "nameself":
            a = member.mention
            b = f"{member.mention}'s"
            return Pronoun(a, a, b, b, f"{member.mention}self")

    if available:
        return random.choice(available)

    return await fetch_pronoun("them")

async def fetch_pronoun(subject: str) -> typing.Optional[Pronoun]:
    if subject in cache:
        return cache[subject]

    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://en.pronouns.page/api/pronouns/{subject}") as response:
            body = await response.text()

            if body == "":
                return None

            try:
                json = await response.json()

            except JSONDecodeError:
                return None

            else:
                pronoun = Pronoun(**json["morphemes"])

                for m in dataclasses.astuple(pronoun):
                    cache[m] = pronoun

                return pronoun
