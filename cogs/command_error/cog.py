import asyncio
import pathlib
import sys
import traceback
import typing
from collections import deque
from io import StringIO

import discord
from discord.ext import commands

from cogs.command_error.capture import FrozenTracebackException, FrameVariablesPair
from cogs.command_error.reactive import TracebackExceptionAnalyzer


def _output_dir(indent, arr, d: dict):
    idx = 0
    for pair in d.items():
        print(pair[1], type(pair[1]))
        output_variable(indent, arr, repr(pair[0]), pair[1])
        idx += 1
        if idx > 10:
            arr.append("\t" * indent + '...\n')
            return


def _output_list(indent, arr, lst: typing.Iterable):
    for idx, value in enumerate(lst):
        output_variable(indent, arr, idx, value)
        if idx > 10:
            arr.append("\t" * indent + '...\n')
            return


def output_variable(indent, arr, name, value):
    for type_, func in custom_output.items():
        if isinstance(value, type_):
            inline_output = object.__repr__(value)
            custom = custom_output[type(value)]
            break
    else:
        if hasattr(value, "stack_variable_output") and callable(value.stack_variable_output):
            inline_output = object.__repr__(value)
            custom = value.stack_variable_output

        else:
            inline_output = repr(value)

            def custom(_, __, ___):
                pass

    arr.append("\t" * indent + f'{name} = {inline_output}\n')
    if indent < 10:
        custom(indent + 1, arr, value)


custom_output = {
    dict: _output_dir,
    (list, tuple): _output_list
}


def generate_custom_stack(type_, value: BaseException, tb, arr=None):
    if arr is None:
        arr = []

    if value.__context__ is not None:
        value = value.__context__
        type_ = type(value)
        tb = value.__traceback__

    arr.extend(traceback.format_exception(type_, value, tb))
    arr.append("\n")

    while True:  # get to the most recent stack
        if tb.tb_next is None:
            break
        tb = tb.tb_next

    frame = tb.tb_frame

    arr.append("Locals:\n")

    _output_dir(1, arr, frame.f_locals)


class CommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.capture = deque(maxlen=10)

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.group()
    async def collected(self, ctx):
        pass

    @collected.command()
    async def trace(self, ctx, idx=0):
        content = self.capture[idx]
        escaped_content = content.replace("```", "``\u200b`")
        message = f"```py\n{escaped_content}```"
        if len(message) >= 2000:  # message limit
            io = StringIO(content)
            await ctx.send(file=discord.File(io, filename="error.txt"))
        else:
            await ctx.send(message)

    @collected.command()
    async def deep(self, ctx, idx=0):
        frozen = self.capture[idx]
        TracebackExceptionAnalyzer(self.bot, ctx.channel, frozen)

    def build_frozen(self, traceback_exception):
        captured_frames = []

        for frame_summary in traceback_exception.stack:
            frame_summary: traceback.FrameSummary

            v = []

            # noinspection PyUnresolvedReferences
            for var, re in frame_summary.locals.items():
                output_variable(0, v, var, re)

            captured_frames.append(FrameVariablesPair(frame_summary.line.strip(), "".join(v)))

            frame_summary.locals = None  # so it doesn't print the variables when formatting the stack

        stack_trace = "".join(traceback_exception.format(chain=False))

        for frame_summary in traceback_exception.stack:
            frame_summary.filename = str(pathlib.Path(*pathlib.Path(frame_summary.filename).parts[-2:]))
            frame_summary._line = f"```py\n{frame_summary.line}```"

        discord_stack_trace = []

        for line in traceback_exception.format(chain=False):
            first_line = line.split("\n")[0]

            final = f"`{first_line}`" + "\n".join(line.split("\n")[1:]) + "\n"

            discord_stack_trace.append(final)

        discord_stack_trace = "".join(discord_stack_trace)

        if traceback_exception.__context__ is not None:
            context = self.build_frozen(traceback_exception.__context__)
        else:
            context = None

        if traceback_exception.__cause__ is not None:
            cause = self.build_frozen(traceback_exception.__cause__)
        else:
            cause = None

        return FrozenTracebackException(captured_frames, stack_trace, discord_stack_trace, cause, context)

    def capture_exception(self, type_, value: BaseException, tb):
        traceback_exception = traceback.TracebackException(type_, value, tb, capture_locals=True)

        captured = self.build_frozen(traceback_exception)

        self.capture.append(captured)
        print("".join(captured.get_full_console_output()), file=sys.stderr)
        print(f"Exception has been collected", file=sys.stderr)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, (commands.CommandInvokeError, commands.ConversionError)):
            self.capture_exception(type(error), error, error.__traceback__)
        elif not isinstance(error, commands.CommandNotFound):
            message = await ctx.send(str(error))
            self.bot.get_cog("Uninvoke").create_unload(ctx.message, lambda: message.delete())

    async def on_error(self, *_, **__):
        error_type, error, tb = sys.exc_info()

        self.capture_exception(error_type, error, tb)


def setup(bot):
    bot.add_cog(CommandError(bot))
