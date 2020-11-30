import discord
from discord.ext import commands


class CommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send(str(error))
        else:
            await ctx.send(str(error))


def setup(bot):
    bot.add_cog(CommandError(bot))
