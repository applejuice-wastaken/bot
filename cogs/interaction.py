import inspect
import operator
import re
from typing import List

import discord
from discord.ext import commands
from discord.ext.commands import MemberConverter, BadArgument

from phrase.build import DeferredReference, build, MaybeReflexive

author = DeferredReference("action_author")
valid = DeferredReference("valid")
rejected = DeferredReference("rejected")
condition = DeferredReference("condition")


def interaction_command_factory(name, *,
                                normal: list,
                                reject: list,
                                condition_rejected: list = author + "could not do this to" + author.reflexive,
                                condition_predicate=lambda _, __: True):
    async def command(self, ctx, *users: RelativeMemberConverter):

        message = await make_response(self, ctx, *users)

        if message is not None:
            async def unload():
                await message.delete()

            ctx.bot.get_cog("Uninvoke").create_unload(ctx.message, unload)

    command.__doc__ = f"executes a {name} action towards selected users, if allowed"

    async def make_response(self, ctx, *users: discord.Member):
        users: List[discord.Member] = list(users)

        if not self.user_accepts(ctx.author, name, "thing"):
            return await ctx.send(f"But you don't like that")

        if ctx.message.reference is not None:
            referenced: discord.Message
            referenced = (ctx.message.reference.cached_message or
                          await ctx.message.channel.fetch_message(ctx.message.reference.message_id))

            users.append(referenced.author)

        allowed = []
        role_denied = []
        condition_denied = []

        for user in users:
            # noinspection PyTypeChecker
            if self.user_accepts(user, name, "thing"):
                if condition_predicate(ctx.author, user):
                    allowed.append(user)
                else:
                    condition_denied.append(user)
            else:
                role_denied.append(user)

        if not users:
            return await ctx.send("No users", allowed_mentions=discord.AllowedMentions.none())

        baking = []

        if allowed:
            baking.extend(normal)

        if allowed and (role_denied or condition_denied):
            baking.append("however")

        if role_denied:
            baking.extend(reject)

        if condition_denied:
            baking.extend(condition_rejected)

        built = await build(baking, speaker=[ctx.bot.user], action_author=ctx.author, valid=allowed,
                            rejected=role_denied, condition=condition_rejected)

        if len(built) > 500:
            return await ctx.send("I would send it the message wasn't this long")

        return await ctx.send(built, allowed_mentions=discord.AllowedMentions.none())

    command = commands.guild_only()(commands.Command(command, name=name))

    # inject command into class by putting it into a variable in it's frame
    inspect.currentframe().f_back.f_locals[f"_command_{name}"] = command


class TooManyExponentials(BadArgument):
    def __init__(self, amount):
        self.amount = amount
        super().__init__('Too many exponentials provided.')


class RelativeConversionNotFound(BadArgument):
    def __init__(self):
        super().__init__('Matching user was not found in last 20 messages.')


class TooManyMessageMentions(BadArgument):
    def __init__(self):
        super().__init__('Message has multiple mentions, ambiguity can occur.')


EXPONENTIAL_REGEX = re.compile(r"^(m?)(\^+)$")


class RelativeMemberConverter(MemberConverter):
    async def convert(self, ctx, argument):
        cache = getattr(ctx, "_cache_relative_member_converter", {})
        if argument in cache:
            return cache[argument]
        else:
            converted = await self.do_convert(ctx, argument)
            cache[argument] = converted
            ctx._cache_relative_member_converter = cache
            return converted

    async def do_convert(self, ctx, argument):
        if argument == "me":
            return ctx.author

        else:
            match = EXPONENTIAL_REGEX.match(argument)
            if match:
                many = len(match.group(2))
                flag = match.group(1)

                if many > 5:
                    raise TooManyExponentials(many)

                last = ctx.author

                async for message in ctx.channel.history(before=ctx.message, limit=20):
                    message: discord.Message
                    if flag == "":
                        if message.author != last:
                            last = message.author
                            many -= 1
                            if many == 0:
                                return await self.query_member_by_id(ctx.bot, ctx.guild, message.author.id) \
                                       or message.author

                    elif flag == "m":
                        if message.mentions:
                            many -= 1
                            if many == 0:
                                if len(message.mentions) == 1:
                                    return await self.query_member_by_id(ctx.bot, ctx.guild, message.mentions[0].id) \
                                           or message.author

                                raw_mentions = message.raw_mentions
                                if len(raw_mentions) == 1:
                                    return await self.query_member_by_id(ctx.bot, ctx.guild, raw_mentions[0]) \
                                           or message.author

                                raise TooManyMessageMentions
                else:
                    raise RelativeConversionNotFound

        return await super(RelativeMemberConverter, self).convert(ctx, argument)


def bulk_delete(sequence, **attrs):
    converted = [
        (operator.attrgetter(attr.replace('__', '.')), value)
        for attr, value in attrs.items()
    ]

    found = []

    for elem in sequence:
        if all(pred(elem) == value for pred, value in converted):
            found.append(elem)

    for obj in found:
        sequence.remove(obj)


class Interaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def user_accepts(self, member, *actions):
        if isinstance(member, discord.User) or member.discriminator == "0000":
            return True

        for action in actions:
            role = discord.utils.get(member.roles, name=f"no {action}")

            allowed = role is None

            if not allowed:
                return False
        return True

    interaction_command_factory("hug",
                                normal=author + "hugs" + MaybeReflexive(author, valid),
                                reject=author + "hugged a lamppost in confusion while trying to hug" + rejected.object)

    interaction_command_factory("kiss",
                                normal=author + "kisses" + MaybeReflexive(author, valid),
                                reject=rejected + "promptly denied the kiss")

    interaction_command_factory("slap",
                                normal=author + "slaps" + MaybeReflexive(author, valid),
                                reject=rejected + "did some weird scooching and avoided" +
                                       author.possessive_determiner + "slap",
                                condition_predicate=operator.ne)

    interaction_command_factory("kill",
                                normal=author + "kills" + MaybeReflexive(author, valid),
                                reject=rejected + "used the totem of undying when" + rejected + "were about to die",
                                condition_predicate=operator.ne)

    interaction_command_factory("stab",
                                normal=author + "stabs" + MaybeReflexive(author, valid),
                                reject=author.possessive_determiner + "knife turned into flowers when it was" +
                                       rejected.possessive_determiner + "turn",
                                condition_predicate=operator.ne)

    interaction_command_factory("stare",
                                normal=author + "stares at" + MaybeReflexive(author, valid),
                                reject=rejected + "turned invisible and" + author +
                                       "was unable to stare at" + rejected.object)

    interaction_command_factory("lick",
                                normal=author + "licks" + MaybeReflexive(author, valid),
                                reject=rejected + "put a cardboard sheet in front before" + author + "was able to lick")

    interaction_command_factory("pet",
                                normal=author + "pets" + MaybeReflexive(author, valid),
                                reject=rejected.possessive_determiner + "head(s) suddenly disappeared")

    interaction_command_factory("pat",
                                normal=author + "pats" + MaybeReflexive(author, valid),
                                reject=author + "pat" + author.reflexive + "in confusion while trying to pat"
                                       + rejected.object)

    interaction_command_factory("cookie",
                                normal=author + "gives a cookie to" + MaybeReflexive(author, valid),
                                reject=rejected + "threw off" + author.possessive_determiner + "cookie")

    interaction_command_factory("attack",
                                normal=author + "attacks" + MaybeReflexive(author, valid),
                                reject=rejected + "teleported away from" + author.object,
                                condition_predicate=operator.ne)

    interaction_command_factory("boop",
                                normal=author + "boops" + MaybeReflexive(author, valid),
                                reject=rejected + "had no nose to boop")

    interaction_command_factory("cuddle",
                                normal=author + "cuddles with" + MaybeReflexive(author, valid),
                                reject=rejected + "looked at" + author.object + "in confusion and walked away")

    interaction_command_factory("cake",
                                normal=author + "gives a cake to" + MaybeReflexive(author, valid),
                                reject=author.possessive_determiner + "cake caught fire when" + author +
                                       "was giving it to" + rejected.object)


def setup(bot):
    bot.add_cog(Interaction(bot))
