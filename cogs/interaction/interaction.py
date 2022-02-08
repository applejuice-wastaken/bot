import operator

import aiohttp.client
from nextcord.ext import commands
from phrase_reference_builder.types import MaybeReflexive, was

from util.pronouns import convert_string_to_pronoun
from .command import interaction_command_factory
from .fragments import author, valid, rejected

NEKO_BOT_BASE = "https://nekos.life/api/v2/"


def neko_bot_get_random(path):
    async def func():
        async with aiohttp.client.ClientSession() as session:
            async with session.get(f"{NEKO_BOT_BASE}/{path}") as response:
                url = (await response.json())["url"]
                return url

    return func


class Interaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.karma = 0

    async def detects_role(self, role):
        return role.name.startswith("no ") or (convert_string_to_pronoun("", role.name)) is not None

    interaction_command_factory("hug",
                                connotation=True,
                                image_processor=neko_bot_get_random("img/hug"),
                                normal=author + " hugs " + MaybeReflexive(author, valid),
                                reject=author + " hugged a lamppost in "
                                                "confusion while trying to hug " + rejected.object)

    interaction_command_factory("kiss",
                                connotation=True,
                                image_processor=neko_bot_get_random("img/kiss"),
                                normal=author + " kisses " + MaybeReflexive(author, valid),
                                reject=rejected + " promptly denied the kiss")

    interaction_command_factory("slap",
                                connotation=False,
                                image_processor=neko_bot_get_random("img/slap"),
                                normal=author + " slaps " + MaybeReflexive(author, valid),
                                reject=(rejected + " did some weird scooching and avoided " +
                                        author.possessive_determiner + " slap"),
                                mutual=False,
                                condition_predicate=operator.ne)

    interaction_command_factory("kill",
                                connotation=False,
                                normal=author + " kills " + MaybeReflexive(author, valid),
                                reject=rejected + " used the totem of undying when " + rejected + " "
                                       + was + " about to die",
                                mutual=False,
                                condition_predicate=operator.ne)

    interaction_command_factory("stab",
                                connotation=False,
                                normal=author + " stabs " + MaybeReflexive(author, valid),
                                reject=(author.possessive_determiner + " knife turned into flowers when it was " +
                                        rejected.possessive_determiner + " turn"),
                                mutual=False,
                                condition_predicate=operator.ne)

    interaction_command_factory("stare",
                                normal=author + " stares at " + MaybeReflexive(author, valid),
                                reject=(rejected + " turned invisible and " + author +
                                        " was unable to stare at " + rejected.object),
                                mutual=False)

    interaction_command_factory("lick",
                                normal=author + " licks " + MaybeReflexive(author, valid),
                                reject=rejected + " put a cardboard sheet in front before " + author +
                                       " was able to lick",
                                mutual=False)

    interaction_command_factory("pet",
                                connotation=True,
                                normal=author + " pets " + MaybeReflexive(author, valid),
                                reject=rejected.possessive_determiner + " head(s) suddenly disappeared",
                                mutual=False)

    interaction_command_factory("pat",
                                connotation=True,
                                normal=author + " pats " + MaybeReflexive(author, valid),
                                reject=(author + " pat " + author.reflexive + " in confusion while trying to pat"
                                        + rejected.object),
                                mutual=False)

    interaction_command_factory("cookie",
                                connotation=True,
                                normal=author + " gives a cookie to " + MaybeReflexive(author, valid),
                                reject=rejected + " threw off " + author.possessive_determiner + " cookie",
                                mutual=False)

    interaction_command_factory("attack",
                                connotation=False,
                                normal=author + " attacks " + MaybeReflexive(author, valid),
                                reject=rejected + " teleported away from " + author.object,
                                condition_predicate=operator.ne,
                                mutual=False)

    interaction_command_factory("boop",
                                connotation=True,
                                normal=author + " boops " + MaybeReflexive(author, valid),
                                reject=rejected + " had no nose to boop",
                                mutual=False)

    interaction_command_factory("cuddle",
                                connotation=True,
                                image_processor=neko_bot_get_random("img/cuddle"),
                                normal=author + " cuddles with " + MaybeReflexive(author, valid),
                                reject=rejected + " looked at " + author.object + " in confusion and walked away")

    interaction_command_factory("cake",
                                connotation=True,
                                normal=author + " gives a cake to " + MaybeReflexive(author, valid),
                                reject=(author.possessive_determiner + " cake caught fire when " + author +
                                        was + " giving it to " + rejected.object),
                                mutual=False)

    interaction_command_factory("cheese",
                                connotation=True,
                                image_processor="https://c.tenor.com/soiGq02-PHUAAAAC/cheese-james-may.gif",
                                normal=author + " gives cheese to " + MaybeReflexive(author, valid),
                                reject=(author.possessive_determiner + " cheese melted away before giving it to "
                                        + rejected.object),
                                mutual=False)


def setup(bot):
    bot.add_cog(Interaction(bot))
