from discord.ext import commands
from discord.ext.commands import CheckFailure


class RequiresCog(CheckFailure):
    def __init__(self, cog):
        super().__init__(f'This command requires the cog {cog}, which is not loaded.')

def requires_cog(cog_name):
    async def predicate(ctx):
        if ctx.bot.get_cog(cog_name) is None:
            raise RequiresCog(cog_name)
        return True
    return commands.check(predicate)
