from __future__ import annotations

import random

import discord
from emoji import UNICODE_EMOJI_ENGLISH
from phrase_reference_builder import build
import typing

from phrase_reference_builder.build import PhraseBuilder, Entity
from phrase_reference_builder.pronouns import Pronoun, PronounType, default_repository, PronounRepository

if typing.TYPE_CHECKING:
    pass


def _add_result_to_repository(repository: PronounRepository):
    def deco(func):
        def wrapped(*args, **kwargs):
            result = func(*args, **kwargs)

            if isinstance(result, Pronoun):
                repository.custom_pronouns.add(result)

            return result
        return wrapped
    return deco


def get_pronouns_from_member(member: discord.Member):
    pronouns = []

    for role in member.roles:
        maybe_pronoun = convert_string_to_pronoun(member.display_name, role.name)

        if maybe_pronoun is not None:
            pronouns.append(maybe_pronoun)

    return pronouns


@_add_result_to_repository(default_repository)
def convert_string_to_pronoun(name: str, string: str):
    if string.startswith("no "):
        return None

    if "/" in string:
        morphemes = [chunk.lower() for chunk in string.split("/")]

        if len(morphemes) == 5:
            return Pronoun.from_tuple(*morphemes,
                                      pronoun_type=PronounType.NEO_PRONOUN, person_class=3,
                                      collective=False)

        elif len(morphemes) == 3:
            return Pronoun.from_tuple(morphemes[0], morphemes[0], morphemes[1], morphemes[1], morphemes[2],
                                      pronoun_type=PronounType.NEO_PRONOUN, person_class=3,
                                      collective=False)

        elif len(morphemes) == 2:
            if morphemes[1].endswith("self"):
                # probably a name of some sort
                return Pronoun.pronounless(morphemes[0])

            elif morphemes[0] == morphemes[1] and morphemes[0] in UNICODE_EMOJI_ENGLISH:
                # probably an emoji pronoun
                pronoun = Pronoun.pronounless(morphemes[0])
                pronoun.pronoun_type = PronounType.EMOJI_PRONOUN
                return pronoun

        for chunk in morphemes:
            pronoun = default_repository.find_pronoun(chunk, person_class=3)

            if pronoun is not None:
                return pronoun

    elif string == "nameself":
        return Pronoun.pronounless(name)


def convert_member(builder: PhraseBuilder, member: discord.Member):
    pronouns = get_pronouns_from_member(member)

    if pronouns:
        pronoun = random.choice(pronouns)

    else:
        pronoun = builder.pronoun_repository.default

    return Entity(member.id, member.display_name, pronoun)


def convert_user(builder: PhraseBuilder, user: discord.User):
    return Entity(user.id, user.name, builder.pronoun_repository.default)


build.conversion_table[discord.Member] = convert_member
build.conversion_table[discord.User] = convert_user
