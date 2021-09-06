import abc
import random
import typing
from json import JSONDecodeError

import aiohttp
import discord
from pydantic import BaseModel

from phrase import pronouns
from phrase.pronouns import PronounType

from emoji import UNICODE_EMOJI


class _Fragment(abc.ABC):
    """Base class that allows addition for more straightforward templating"""

    @classmethod
    def _compute_add(cls, this, other):
        if not isinstance(this, _FragmentList):
            this = [this]

        if not isinstance(other, _FragmentList):
            other = [other]

        return _FragmentList([*this, *other])

    def __add__(self, other):
        return self._compute_add(self, other)

    def __radd__(self, other):
        return self._compute_add(other, self)


class _FragmentList(_Fragment, list):
    pass


class _Resolvable(abc.ABC):
    """Base class that resolves self to a string or another resolvable"""

    @abc.abstractmethod
    async def resolve(self, context: "BuildingContext", self_idx: typing.Optional[int]):
        pass


class Entity:
    def __init__(self, id_, name: str, pronoun: pronouns.Pronoun):
        self.id = id_

        self.name = name
        self.pronounless = pronouns.Pronoun.pronounless(self.name)
        self.pronoun = pronoun

    def __eq__(self, other):
        return isinstance(other, Entity) and self.id == other.id


class PhraseBuilder:
    def __init__(self):
        self.referenced = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @classmethod
    async def figure_pronouns(cls, member: discord.Member, *,
                              return_default=True,
                              return_multiple=False) -> typing.Union[None,
                                                                     pronouns.Pronoun,
                                                                     typing.List[pronouns.Pronoun]]:

        if not hasattr(member, "roles"):
            return ([pronouns.default] if return_multiple else pronouns.default) if return_default else None

        available = []

        for role in member.roles:
            maybe_pronoun = await cls.figure_pronouns_from_role(member, role)

            if maybe_pronoun is not None:
                available.append(maybe_pronoun)

        if available:
            if return_multiple:
                return available
            else:
                return random.choice(available)

        return ([pronouns.default] if return_multiple else pronouns.default) if return_default else None

    @classmethod
    async def figure_pronouns_from_role(cls, member: discord.Member, role: discord.Role):
        if "/" in role.name:
            chunks = [chunk.lower() for chunk in role.name.split("/")]

            if len(chunks) == 5:
                return pronouns.Pronoun.from_tuple(*chunks,
                                                   pronoun_type=PronounType.NEO_PRONOUN, person_class=3,
                                                   collective=False)

            elif len(chunks) == 3:
                return pronouns.Pronoun.from_tuple(chunks[0], chunks[0], chunks[1], chunks[1], chunks[2],
                                                   pronoun_type=PronounType.NEO_PRONOUN, person_class=3,
                                                   collective=False)

            elif len(chunks) == 2:
                if chunks[1].endswith("self"):
                    # probably a name of some sort
                    return pronouns.Pronoun.pronounless(chunks[0])

                elif chunks[0] == chunks[1] and chunks[0] in UNICODE_EMOJI["en"]:
                    # probably an emoji pronoun
                    pronoun = pronouns.Pronoun.pronounless(chunks[0])
                    pronoun.pronoun_type = PronounType.EMOJI_PRONOUN
                    return pronoun

            # all conventional ways of getting this pronoun have failed
            # go the hard way

            for chunk in chunks:
                pronoun = await cls.fetch_pronoun(chunk)

                if pronoun is not None:
                    return pronoun

        elif role.name == "nameself":
            return pronouns.Pronoun.pronounless(member.display_name if hasattr(member, "display_name") else member)

    @classmethod
    async def fetch_pronoun(cls, subject: str) -> typing.Optional[pronouns.Pronoun]:
        pronoun = pronouns.find_pronoun(subject, person_class=3)
        if pronoun:
            return pronoun

        if subject in pronouns.unknown_morphemes:
            return None

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://en.pronouns.page/api/pronouns/{subject}") as response:
                body = await response.text()

                if body == "":
                    pronouns.unknown_morphemes.append(subject)
                    return None

                try:
                    json = await response.json()

                except JSONDecodeError:
                    pronouns.unknown_morphemes.append(subject)
                    return None

                else:
                    json["morphemes"]["subject"] = json["morphemes"]["pronoun_subject"]
                    json["morphemes"]["object"] = json["morphemes"]["pronoun_object"]

                    del json["morphemes"]["pronoun_subject"]
                    del json["morphemes"]["pronoun_object"]

                    pronoun = pronouns.Pronoun(**json["morphemes"],
                                               pronoun_type=PronounType.NEO_PRONOUN, person_class=3, collective=False)

                    pronouns.known_pronouns.append(pronoun)

                    return pronoun

    async def _identify_deferred_dict(self, dict_list):
        ret = {}

        for defer_name, defer_user in dict_list.items():
            ret[defer_name] = await self.convert_to_entity_collection(defer_user)

        return ret

    async def convert_to_entity_collection(self, users):
        if not isinstance(users, list):
            users = [users]

        users: typing.List[discord.Member]

        return [Entity(user.id, user.display_name, await self.figure_pronouns(user)) for user in users]

    async def build(self, fragments: list, *, speaker=None, author=None, deferred: typing.Dict):
        deferred = await self._identify_deferred_dict(deferred)

        if speaker is not None:
            speaker = await self.convert_to_entity_collection(speaker)

        if author is not None:
            author = await self.convert_to_entity_collection(author)

        context = BuildingContext(builder=self,
                                  building=[],
                                  speaker=speaker,
                                  author=author,
                                  deferred=deferred)

        for fragment in fragments:
            context.building.append([fragment])

        for idx, building_list in enumerate(context.building):
            while isinstance(building_list[-1], _Resolvable):
                building_list.append(await building_list[-1].resolve(context, idx))

            if not isinstance(building_list[-1], str):
                raise RuntimeError(f"Bad Resolve: {type(building_list[-1])}")

        return " ".join([ret[-1] for ret in context.building])


class BuildingContext(BaseModel):
    builder: PhraseBuilder

    building: typing.List[typing.List[typing.Union[_Resolvable, str]]]

    speaker: typing.Optional[typing.List[Entity]]
    author: typing.Optional[typing.List[Entity]]
    deferred: typing.Dict[str, typing.List[Entity]]

    class Config:
        arbitrary_types_allowed = True
