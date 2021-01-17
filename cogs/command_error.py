import sys
import traceback
import types
import discord
from discord.ext import commands


class CommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        sys.excepthook = self.advanced

    def advanced(self, type, value: BaseException, tb):
        value = getattr(value, "__cause__", value)
        traceback.print_exception(type, value, tb)
        for_locals = True
        for active_vars in [tb.tb_frame.f_locals, tb.tb_frame.f_globals]:
            header = 'Locals:' if for_locals else 'Globals:'
            print(header, file=sys.stderr)
            for k, v in active_vars.items():
                if not (k.startswith('__') and k.endswith('__') and not isinstance(v, types.TracebackType)):
                    print(f'\t{k} = {v}', file=sys.stderr)
            for_locals = False

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not isinstance(error, commands.CommandInvokeError):
            await ctx.send(str(error))
        else:
            self.advanced(type(error), error, error.__traceback__)


def setup(bot):
    bot.add_cog(CommandError(bot))
