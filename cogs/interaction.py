import inspect
import re
from collections import deque, namedtuple
from typing import List

import discord
from discord.ext import commands
import operator

from discord.ext.commands import MemberConverter, BadArgument

from util.human_join_list import human_join_list


def interaction_command_factory(name, action, condition=lambda _, __: True):
    custom_function = None

    async def command(self, ctx, *users: RelativeMemberConverter):

        message = await make_response(self, ctx, *users)

        if message is not None:
            async def unload():
                await message.delete()

            ctx.bot.get_cog("Uninvoke").create_unload(ctx.message, unload)

    command.__doc__ = f"executes a {name} action towards selected users, if allowed"

    async def make_response(self, ctx, *users: discord.Member):
        def transform(u):
            if u == ctx.author:
                return "themselves"
            elif u == ctx.bot.user:
                return "me"
            else:
                return u.name

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

        if callable(custom_function):
            ret = await custom_function(self, ctx, allowed, role_denied, condition_denied)
            if ret is not None:
                return ret

        allowed = [transform(user) for user in allowed]
        role_denied = [transform(user) for user in role_denied]
        condition_denied = [transform(user) for user in condition_denied]

        if not users:
            return await ctx.send(f"{ctx.author.name} {action} the air...?",
                                  allowed_mentions=discord.AllowedMentions.none())

        if allowed:
            acted = f"{ctx.author.name} {action} {human_join_list(allowed)}"

        if role_denied:
            disallowed_fragments.append(f"{human_join_list(role_denied)} did not allow them to do this")

        if condition_denied:
            disallowed_fragments.append(f"they could not do this with {human_join_list(condition_denied)}")

        final = []
        if acted is not None:
            final.append(acted)

        if disallowed_fragments:
            final.append(human_join_list(disallowed_fragments, True))

        to_send = " but ".join(final)

        if len(to_send) > 500:
            return await ctx.send("I would send it the message wasn't this long")

        return await ctx.send(to_send, allowed_mentions=discord.AllowedMentions.none())

    command = commands.guild_only()(commands.Command(command, name=name))

    # inject command into class by putting it into a variable in it's frame
    inspect.currentframe().f_back.f_locals[f"_command_{name}"] = command

    def wrapper(func):
        nonlocal custom_function
        custom_function = func

    return wrapper


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
                                return await self.query_member_by_id(ctx.bot, ctx.guild, message.author.id)

                    elif flag == "m":
                        if message.mentions:
                            many -= 1
                            if many == 0:
                                if len(message.mentions) == 1:
                                    return await self.query_member_by_id(ctx.bot, ctx.guild, message.mentions[0].id)

                                raw_mentions = message.raw_mentions
                                if len(raw_mentions) == 1:
                                    return await self.query_member_by_id(ctx.bot, ctx.guild, raw_mentions[0])

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


CacheRecord = namedtuple("CacheRecord", "guild_id member_id action value")


class Interaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.command_cache = deque(maxlen=100)

    def user_accepts(self, member, *actions):
        for action in actions:
            cached = discord.utils.get(self.command_cache, guild_id=member.guild.id, member_id=member.id, action=action)

            if cached is None:
                role = discord.utils.get(member.roles, name=f"no {action}")

                allowed = role is None

                self.command_cache.append(CacheRecord(guild_id=member.guild.id,
                                                      member_id=member.id,
                                                      action=action,
                                                      value=allowed))
            else:
                allowed = cached.value

            if not allowed:
                return False
        return True

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.name.startswith("no "):
            bulk_delete(self.command_cache, guild_id=before.guild.id, action=before.name[3:])

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        bulk_delete(self.command_cache, member_id=before.id)

    @interaction_command_factory("hug", "hugs")
    async def custom_hug(self, ctx, allowed, role_denied, condition_denied):
        if (not allowed or (len(allowed) == 1 and ctx.author in allowed)) \
                and not role_denied and not condition_denied:
            return await ctx.send("I think someone here needs a hug.")

    interaction_command_factory("kiss", "kisses")
    interaction_command_factory("slap", "slaps", operator.ne)
    interaction_command_factory("kill", "kills", operator.ne)
    interaction_command_factory("stab", "stabs", operator.ne)
    interaction_command_factory("stare", "stares at")
    interaction_command_factory("lick", "licks")
    interaction_command_factory("pet", "pets")
    interaction_command_factory("pat", "pats")
    interaction_command_factory("cookie", "gives a cookie to")
    interaction_command_factory("attack", "attacks", operator.ne)
    interaction_command_factory("boop", "boops")
    interaction_command_factory("cuddle", "cuddles with")


def setup(bot):
    bot.add_cog(Interaction(bot))
