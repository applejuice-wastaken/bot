import discord
from discord.ext import commands
import operator

from util.human_join_list import human_join_list


def interaction_command_factory(name, action, condition=lambda _, __: True):
    async def wrapped(self, ctx, *users: discord.Member):
        role = discord.utils.get(ctx.author.roles, name=f"no {name}")
        if role is not None:
            await ctx.send(f"But you don't like that")
            return

        if not users:
            await ctx.send(f"{ctx.author.mention} {action} the air...?", allowed_mentions=discord.AllowedMentions.none())
            return

        allowed = []
        role_denied = []
        condition_denied = []

        for user in users:
            role = discord.utils.get(user.roles, name=f"no {name}")
            mention = "themselves" if user == ctx.author else user.mention
            if role is None:
                if condition(ctx.author, user):
                    allowed.append(mention)
                else:
                    condition_denied.append(mention)
            else:
                role_denied.append(mention)

        acted = None
        disallowed_fragments = []

        if allowed:
            acted = f"{ctx.author.mention} {action} {human_join_list(allowed)}"

        if role_denied:
            disallowed_fragments.append(f"{human_join_list(role_denied)} did not allow you to do this")

        if condition_denied:
            disallowed_fragments.append(f"you could not do this with {human_join_list(condition_denied)}")

        final = []
        if acted is not None:
            final.append(acted)

        if disallowed_fragments:
            final.append(human_join_list(disallowed_fragments, True))

        await ctx.send(" but ".join(final), allowed_mentions=discord.AllowedMentions.none())
    return commands.guild_only()(commands.command(name=name)(wrapped))

class Interaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
