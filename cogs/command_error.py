import sys
import traceback
import types
import discord
import inspect
from discord.ext import commands

def output_dir(d: dict):
    idx = 0
    for pair in d.items():
        print(f'\t\t{repr(pair[0])} = {repr(pair[1])}', file=sys.stderr)
        idx += 1
        if idx > 10:
            print(f'\t\t...', file=sys.stderr)
            return

def output_list(lst: list):
    for idx, value in enumerate(lst):
        print(f'\t\t{idx} = {repr(value)}', file=sys.stderr)
        if idx > 10:
            print(f'\t\t...', file=sys.stderr)
            return


custom_output = {
    dict: output_dir,
    list: output_list
}

class CommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        sys.excepthook = self.advanced

    def advanced(self, type_, value: BaseException, tb):
        if value.__context__ is not None:
            value = value.__context__
            type_ = type(value)
            tb = value.__traceback__

        traceback.print_exception(type_, value, tb)
        print(file=sys.stderr)
        for_locals = True

        while True:
            if tb.tb_next is None:
                break
            tb = tb.tb_next
        frame = tb.tb_frame

        for active_vars in [frame.f_locals, frame.f_globals]:
            header = 'Locals:' if for_locals else 'Globals:'
            print(header, file=sys.stderr)
            for k, v in active_vars.items():
                if not (k.startswith('__') and k.endswith('__') and not inspect.ismodule(v)):

                    if type(v) in custom_output:
                        inline_output = object.__repr__(v)
                        custom = custom_output[type(v)]
                    else:
                        inline_output = repr(v)

                        def custom(_):
                            pass

                    print(f'\t{k} = {inline_output}', file=sys.stderr)
                    custom(v)
            for_locals = False

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not isinstance(error, (commands.CommandInvokeError, commands.CommandNotFound)):
            await ctx.send(str(error))
        elif isinstance(error, commands.CommandInvokeError):
            print("Error while executing command", file=sys.stderr)
            self.advanced(type(error), error, error.__traceback__)

    @commands.Cog.listener()
    async def on_error(self, name, *args, **kwargs):
        error_type, error, tb = sys.exc_info()
        if isinstance(error, commands.CommandInvokeError):
            print(f"Error while executing event {name}", file=sys.stderr)
            print(f"Args: {args}", file=sys.stderr)
            print(f"Kwargs: {kwargs}", file=sys.stderr)
            print(file=sys.stderr)
            self.advanced(error_type, error, tb)

def setup(bot):
    bot.add_cog(CommandError(bot))
