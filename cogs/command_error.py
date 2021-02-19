import inspect
import sys
import traceback

from discord.ext import commands


# noinspection PyTypeChecker
def _output_dir(indent, d: dict):
    idx = 0
    for pair in d.items():
        output_variable(indent, repr(pair[0]), repr(pair[1]))
        idx += 1
        if idx > 10:
            print("\t" * indent + '...', file=sys.stderr)
            return


def _output_list(indent, lst: list):
    for idx, value in enumerate(lst):
        output_variable(indent, idx, value)
        if idx > 10:
            print("\t" * indent + '...', file=sys.stderr)
            return


def output_variable(indent, name, value):
    if type(value) in custom_output:
        inline_output = object.__repr__(value)
        custom = custom_output[type(value)]

    elif hasattr(value, "stack_variable_output") and callable(value.stack_variable_output):
        inline_output = object.__repr__(value)
        custom = value.stack_variable_output

    else:
        inline_output = repr(value)

        def custom(_, __):
            pass

    print("\t" * indent + f'{name} = {inline_output}', file=sys.stderr)
    if indent < 10:
        custom(indent + 1, value)


custom_output = {
    dict: _output_dir,
    list: _output_list
}


class CommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        clazz = type(self.bot)
        self.old = clazz.on_error
        clazz.on_error = self.on_error
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
                if not (k.startswith('__') and k.endswith('__')) and not inspect.ismodule(v):
                    output_variable(1, k, v)

            for_locals = False

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not isinstance(error, (commands.CommandInvokeError, commands.CommandNotFound)):
            await ctx.send(str(error))
        elif isinstance(error, commands.CommandInvokeError):
            print("Error while executing command", file=sys.stderr)
            self.advanced(type(error), error, error.__traceback__)

    async def on_error(self, name, *args, **kwargs):
        error_type, error, tb = sys.exc_info()

        print(f"Error while executing event {name}", file=sys.stderr)
        print(f"Args: {args}", file=sys.stderr)
        print(f"Kwargs: {kwargs}", file=sys.stderr)
        print(file=sys.stderr)
        self.advanced(error_type, error, tb)

    def cog_unload(self):
        clazz = type(self.bot)
        clazz.on_error = self.old


def setup(bot):
    bot.add_cog(CommandError(bot))
