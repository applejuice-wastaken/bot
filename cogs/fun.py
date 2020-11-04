import discord
from discord.ext import commands

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="doggo")
    async def dog(self, ctx):
        m = await ctx.send("doggo")
        self.bot.get_cog("Uninvoke").create_unload(ctx.message, lambda: m.delete())


def setup(bot):
    bot.add_cog(Fun(bot))
