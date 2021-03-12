from collections import deque, namedtuple
from typing import List

import discord
from discord.ext import commands
import operator

from discord.ext.commands import MemberConverter, BadArgument

from util.human_join_list import human_join_list


def interaction_command_factory(name, action, condition=lambda _, __: True):
    async def command(self, ctx, *users: RelativeMemberConverter):
        message = await make_response(self, ctx, *users)

        if message is not None:
            async def unload():
                await message.delete()

            ctx.bot.get_cog("Uninvoke").create_unload(ctx.message, unload)

    async def make_response(self, ctx, *users: discord.Member):
        self: Interaction
        users: List[discord.Member]

        if not self.user_accepts(ctx.author, name, "thing"):
            return await ctx.send(f"But you don't like that")

        if not users:
            return await ctx.send(f"{ctx.author.name} {action} the air...?", allowed_mentions=discord.AllowedMentions.none())

        allowed = []
        role_denied = []
        condition_denied = []

        for user in users:
            if user == ctx.author:
                mention = "themselves"
            elif user == ctx.bot.user:
                mention = "me"
            else:
                mention = user.name

            # noinspection PyTypeChecker
            if self.user_accepts(user, name, "thing"):
                if condition(ctx.author, user):
                    allowed.append(mention)
                else:
                    condition_denied.append(mention)
            else:
                role_denied.append(mention)

        acted = None
        disallowed_fragments = []

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
    return commands.guild_only()(commands.command(name=name)(command))

class TooManyExponentials(BadArgument):
    def __init__(self, amount):
        self.amount = amount
        super().__init__('Too many exponentials provided.')

class RelativeMemberConverter(MemberConverter):
    async def convert(self, ctx, argument):
        if argument == "me":
            return ctx.author

        elif argument[1:] == argument[:-1] and argument[0] == "^":  # if the argument is a sequence of ^
            many = len(argument)  # get number of ^

            if many > 5:
                raise TooManyExponentials(many)

            last = ctx.author

            async for message in ctx.channel.history(before=ctx.message):
                message: discord.Message
                if message.author != last:
                    last = message.author
                    many -= 1
                    if many == 0:
                        return await self.query_member_by_id(ctx.bot, ctx.guild, message.author.id)

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

    hug = interaction_command_factory("hug", "hugs")
    kiss = interaction_command_factory("kiss", "kisses")
    slap = interaction_command_factory("slap", "slaps")
    kill = interaction_command_factory("kill", "kills", operator.ne)
    stab = interaction_command_factory("stab", "stabs", operator.ne)
    disappoint = interaction_command_factory("disappoint", "looks in disappointment to", operator.ne)
    stare = interaction_command_factory("stare", "stares at")
    lick = interaction_command_factory("lick", "licks")
    pet = interaction_command_factory("pet", "pets")
    pat = interaction_command_factory("pat", "pats")
    cookie = interaction_command_factory("cookie", "gives a cookie to")
    attack = interaction_command_factory("attack", "attacks")

def setup(bot):
    bot.add_cog(Interaction(bot))
