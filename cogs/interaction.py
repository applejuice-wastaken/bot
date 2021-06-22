import asyncio
import inspect
import operator
import re
from typing import List

import discord
from discord.ext import commands
from discord.ext.commands import MemberConverter, BadArgument

from util.human_join_list import human_join_list
from util.pronouns import figure_pronouns, default


def interaction_command_factory(name, *, normal_str: str, rejected_str: str = "{1} did not allow {0} to do this",
                                condition_rejected_str: str = "{0} could not do this to {1}", connotation=0,
                                condition=lambda _, __: True):

    async def command(self, ctx, *users: RelativeMemberConverter):

        message = await make_response(self, ctx, *users)

        if message is not None:
            async def unload():
                await message.delete()

            ctx.bot.get_cog("Uninvoke").create_unload(ctx.message, unload)

    command.__doc__ = f"executes a {name} action towards selected users, if allowed"

    async def make_response(self, ctx, *users: discord.Member):
        try:
            pronoun = await asyncio.wait_for(asyncio.shield(figure_pronouns(ctx.author)), 1)

        except asyncio.TimeoutError:
            print("too long")
            pronoun = default

        def transform(u):
            if u == ctx.author:
                return pronoun.reflexive
            elif u == ctx.bot.user:
                if connotation == -1:
                    smile = " :("
                elif connotation == 1:
                    smile = " :)"
                else:
                    smile = ""

                return f"me{smile}"
            else:
                return u.display_name

        self: Interaction
        users: List[discord.Member]

        if not self.user_accepts(ctx.author, name, "thing"):
            return await ctx.send(f"But you don't like that")

        allowed = []
        role_denied = []
        condition_denied = []

        for user in users:
            # noinspection PyTypeChecker
            if self.user_accepts(user, name, "thing"):
                if condition(ctx.author, user):
                    allowed.append(user)
                else:
                    condition_denied.append(user)
            else:
                role_denied.append(user)

        acted = None
        disallowed_fragments = []

        allowed = [transform(user) for user in allowed]
        role_denied = [transform(user) for user in role_denied]
        condition_denied = [transform(user) for user in condition_denied]

        if not users:
            return await ctx.send(normal_str.format(ctx.author.name, "the air"),
                                  allowed_mentions=discord.AllowedMentions.none())

        referenced_name = False

        if allowed:
            acted = normal_str.format(ctx.author.display_name, human_join_list(allowed))
            referenced_name = True

        if role_denied:
            disallowed_fragments.append(rejected_str.format(pronoun.pronoun_object if referenced_name
                                                            else ctx.author.name, human_join_list(role_denied)))
            referenced_name = True

        if condition_denied:
            disallowed_fragments.append(condition_rejected_str.format(pronoun.pronoun_subject if referenced_name
                                                                      else ctx.author.name,
                                                                      human_join_list(condition_denied)))

        final = []
        if acted is not None:
            final.append(acted)

        if disallowed_fragments:
            final.append(human_join_list(disallowed_fragments, analyse_contents=True))

        to_send = " but ".join(final)

        if len(to_send) > 500:
            return await ctx.send("I would send it the message wasn't this long")

        return await ctx.send(to_send, allowed_mentions=discord.AllowedMentions.none())

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

    interaction_command_factory("hug", normal_str="{0} hugs {1}",
                                rejected_str="they hugged a lamp post trying to hug {1}")

    interaction_command_factory("kiss", normal_str="{0} kisses {1}", rejected_str="{1} promptly denied the kiss")

    interaction_command_factory("slap", normal_str="{0} slaps {1}",
                                rejected_str="{1} did some weird scooching and avoided the slap", condition=operator.ne)

    interaction_command_factory("kill", normal_str="{0} kills {1}", rejected_str="{1} used the totem of undying",
                                condition=operator.ne)

    interaction_command_factory("stab", normal_str="{0} stabs {1}",
                                rejected_str="the knife's blade magically melted off while trying to stab {1}",
                                condition=operator.ne)

    interaction_command_factory("stare", normal_str="{0} stares at {1}", rejected_str="{1} turned invisible")

    interaction_command_factory("lick", normal_str="{0} licks {1}")

    interaction_command_factory("pet", normal_str="{0} pets {1}", rejected_str="{1} head(s) suddenly disappeared")

    interaction_command_factory("pat", normal_str="{0} pats {1}", rejected_str="{0} hand pat {0} instead while "
                                                                               "trying to pat {1}")

    interaction_command_factory("cookie", normal_str="{0} gives a cookie to {1}",
                                rejected_str="{1} threw off the cookie")

    interaction_command_factory("attack", normal_str="{0} attacks {1}", rejected_str="{1} threw off the cookie",
                                condition=operator.ne)

    interaction_command_factory("boop", normal_str="{0} boops {1}", rejected_str="{1} had no nose")

    interaction_command_factory("cuddle", normal_str="{0} cuddles with {1}",
                                rejected_str="{1} looked at you in confusion and walked away")

    interaction_command_factory("cake", normal_str="{0} gives cake to {1}",
                                rejected_str="the cake turned into ash when it was given to {1}")


def setup(bot):
    bot.add_cog(Interaction(bot))
