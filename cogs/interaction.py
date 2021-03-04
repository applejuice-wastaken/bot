import discord
from discord.ext import commands
import operator

def interaction_command_factory(name, action, condition=lambda _, __: True):
    async def wrapped(self, ctx, user: discord.Member):
        role = discord.utils.get(ctx.author.roles, name=f"no {name}")
        if role is not None:
            await ctx.send(f"But you don't like that")
            return

        role = discord.utils.get(user.roles, name=f"no {name}")
        if role is not None:
            await ctx.send(f"I guess {user.mention} does not like that",
                           allowed_mentions=discord.AllowedMentions.none())
            return

        if condition(ctx.author, user):
            target = "themselves" if user == ctx.author else user.mention
            await ctx.send(f"{ctx.author.mention} {action} {target}",
                           allowed_mentions=discord.AllowedMentions.none())
        else:
            await ctx.send("You can't do that!")
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
