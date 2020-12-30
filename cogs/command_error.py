import traceback

import discord
from discord.ext import commands


class CommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send(str(error))
        elif str(self.bot.get_env_value("show_command_error")) == "True":
            traceback.print_exception(type(error), error, error.__traceback__)

def setup(bot):
    bot.add_cog(CommandError(bot))
