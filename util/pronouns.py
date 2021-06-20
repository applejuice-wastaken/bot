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
    normative: bool = False

    def __str__(self):
        if self.normative:
            return f"{self.pronoun_subject}/{self.pronoun_object}"

        else:
            return f"{self.pronoun_subject}/{self.pronoun_object}/{self.possessive_determiner}/" \
                   f"{self.possessive_pronoun}/{self.reflexive}"


cache = {"he": Pronoun("he", "him", "his", "his", "himself", True),
         "she": Pronoun("she", "her", "her", "hers", "herself", True),
         "they": Pronoun("they", "them", "their", "theirs", "themselves", True)}

default = cache["they"]


async def figure_pronouns(member: discord.Member, *, return_default=True,
                          return_multiple=False) -> typing.Union[None, Pronoun, typing.List[Pronoun]]:
    if isinstance(member, discord.User) or member.discriminator == "0000":
        return ([default] if return_multiple else default) if return_default else None

    available = []

    for role in member.roles:
        role: discord.Role

        if "/" in role.name:
            chunks = role.name.split("/")

            pronoun = None

            if len(chunks) == 5:
                pronoun = Pronoun(*chunks)

            elif len(chunks) == 3:
                pronoun = Pronoun(chunks[0], chunks[0], chunks[1], chunks[1], chunks[2])

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
            pronoun = Pronoun(a, a, b, b, f"{member.mention}self")
            return [pronoun] if return_multiple else pronoun

    if available:
        if return_multiple:
            return available
        else:
            return random.choice(available)

    return ([default] if return_multiple else default) if return_default else None


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

                cache[pronoun.pronoun_subject] = pronoun

                return pronoun
