import inspect
import sys
import traceback
from io import StringIO
from collections import deque

import typing

import discord
from discord.ext import commands


def _output_dir(indent, returned, d: dict):
    idx = 0
    for pair in d.items():
        output_variable(indent, returned, repr(pair[0]), pair[1])
        idx += 1
        if idx > 10:
            returned.append("\t" * indent + '...\n')
            return


def _output_list(indent, returned, lst: typing.Iterable):
    for idx, value in enumerate(lst):
        output_variable(indent, returned, idx, value)
        if idx > 10:
            returned.append("\t" * indent + '...\n')
            return


def output_variable(indent, returned, name, value):
    if type(value) in custom_output:
        inline_output = object.__repr__(value)
        custom = custom_output[type(value)]

    elif hasattr(value, "stack_variable_output") and callable(value.stack_variable_output):
        inline_output = object.__repr__(value)
        custom = value.stack_variable_output

    else:
        inline_output = repr(value)

        def custom(_, __, ___):
            pass

    returned.append("\t" * indent + f'{name} = {inline_output}\n')
    if indent < 10:
        custom(indent + 1, returned, value)


custom_output = {
    dict: _output_dir,
    list: _output_list
}


def generate_custom_stack(type_, value: BaseException, tb, ret=None):
    if ret is None:
        ret = []

    if value.__context__ is not None:
        value = value.__context__
        type_ = type(value)
        tb = value.__traceback__

    ret.extend(traceback.format_exception(type_, value, tb))
    ret.append("\n")

    while True:  # get to the most recent stack
        if tb.tb_next is None:
            break
        tb = tb.tb_next

    frame = tb.tb_frame

    ret.append("Locals:\n")

    for k, v in frame.f_locals.items():
        if not (k.startswith('__') and k.endswith('__')) and not inspect.ismodule(v):
            output_variable(1, ret, k, v)

    return ret


class CommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.capture = deque(maxlen=10)

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command()
    async def collect(self, ctx, idx=0):
        content = self.capture[idx]
        escaped_content = content.replace("```", "``\u200b`")
        message = f"```py\n{escaped_content}```"
        if len(message) >= 2000:  # message limit
            io = StringIO(content)
            await ctx.send(file=discord.File(io, filename="error.txt"))
        else:
            await ctx.send(message)

    def capture_exception(self, type_, value: BaseException, tb, returner=None):
        stack = "".join(generate_custom_stack(type_, value, tb, returner))
        self.capture.append(stack)
        print(stack, file=sys.stderr)
        print(f"Exception has been collected", file=sys.stderr)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not isinstance(error, (commands.CommandInvokeError, commands.CommandNotFound)):
            await ctx.send(str(error))
        elif isinstance(error, commands.CommandInvokeError):
            self.capture_exception(type(error), error, error.__traceback__,
                                   ["Error while executing command\n"])

    async def on_error(self, name, *args, **kwargs):
        error_type, error, tb = sys.exc_info()

        header = [f"Error while executing event {name}\n", f"Args:\n"]

        _output_list(1, header, args)
        header.append("Kwargs:\n")
        _output_dir(1, header, kwargs)

        self.capture_exception(error_type, error, tb, header)


def setup(bot):
    bot.add_cog(CommandError(bot))
