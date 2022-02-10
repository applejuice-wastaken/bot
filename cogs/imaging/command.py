import asyncio
import difflib
import inspect
import typing
from io import BytesIO
from typing import TYPE_CHECKING

import nextcord
from PIL import Image
from nextcord import Interaction, SlashOption
from nextcord.ext import commands
from render.execute import run_scene

from cogs.imaging.executor import execute
from cogs.imaging.flag_retriever import Flag, search
from cogs.imaging.resize import stitch_flags, try_get_image
from cogs.imaging.scenery import RotateDirection
from util.interops import CommandInterop, TraditionalCommandInterop

if TYPE_CHECKING:
    from cogs.imaging import Imaging


def generic_flag_command(name):
    def wrapper(func):
        async def impl_command(resp: CommandInterop,
                               cog: "Imaging",
                               user: typing.Optional[nextcord.Member],
                               *flags: Flag,
                               rotate: RotateDirection = RotateDirection.NO,
                               fps: int = 60):

            if len(flags) == 0:
                await resp.respond(f"no flags provided", failure=True)
                return

            if cog.execution_semaphore.locked():
                await resp.respond("Awaiting for slots")

            async with cog.execution_semaphore:
                using_chunk = resp.chunk()

                if len(flags) == 1:
                    await using_chunk.set(f"using `{flags[0].name}` flag provided by {flags[0].provider}")

                else:
                    listing = "\n".join(f"    `{flag.name}` flag provided by {flag.provider}" for flag in flags)
                    await using_chunk.set(f"using:\n{listing}")

                async with resp.loading():
                    opened_flags = []
                    flags_url = {}

                    for flag in flags:
                        if flag.url in flags_url:
                            opened_flags.append(flags_url[flag.url])
                        else:
                            image = await flag.open()
                            opened_flags.append(image)
                            flags_url[flag.url] = image

                    if isinstance(resp, TraditionalCommandInterop):
                        user_bin = await try_get_image(resp.ctx, user)

                    else:
                        user_bin = await user.avatar.read()

                    user = await execute(Image.open, BytesIO(user_bin))

                    if len(opened_flags) == 1:
                        stitched_flag = opened_flags[0]

                    else:
                        stitched_flag = await execute(stitch_flags, user.size, *opened_flags)

                    scene = await execute(func, cog, user, stitched_flag, rotate=rotate, fps=fps)
                    io, animated = await execute_scene(resp, scene)

                    if io is not None:
                        io.seek(0)
                        using_chunk.remove()
                        await resp.respond(content="Render complete",
                                           file=nextcord.File(io, f"output.{'gif' if animated else 'png'}"))

        async def c_single(self, ctx, user: typing.Optional[nextcord.Member], *, flag: Flag):
            await impl_command(CommandInterop.from_command(ctx), self, user, flag)

        async def s_command(self, interaction: Interaction,
                            flag_names=SlashOption("flag_names",
                                                   description="The names of the flags, separated by commas"),

                            rotates: int = SlashOption("rotating", description="the direction the flag should rotate",
                                                       choices={
                                                           "No rotation": RotateDirection.NO.value,
                                                           "Counter clockwise": RotateDirection.COUNTERCLOCKWISE.value,
                                                           "Clockwise": RotateDirection.CLOCKWISE.value
                                                       },
                                                       required=False, default=RotateDirection.NO.value),

                            fps: int = SlashOption("fps", description="the frames per second of the output",
                                                   required=False, default=60, max_value=60, min_value=1),
                            ):
            flag_names: str

            flags = []

            for flag_name in flag_names.split(","):
                flags.append(await Flag.convert(None, flag_name.strip()))

            await impl_command(CommandInterop.from_slash_interaction(interaction),
                               self, interaction.user, *flags, rotate=RotateDirection(rotates), fps=fps)

        async def c_mixin(self, ctx, user: typing.Optional[nextcord.Member], *flags: Flag):
            await impl_command(CommandInterop.from_command(ctx), self, user, *flags)

        s_command = (nextcord.slash_command(name=name, description=func.__doc__, guild_ids=[473890635972083733])
                     (s_command))

        @s_command.on_autocomplete("flag_names")
        async def s_command_auto_flag_names(self, interaction: Interaction, raw: str):
            split = raw.rsplit(",", maxsplit=1)

            current = split[-1]

            if ":" in current:
                chunks = current.split(":", maxsplit=1)
                ret = await search(chunks[1], chunks[0])
                ret = set(f"{chunks[0]}:{res}" for res in ret)
            else:
                ret = await search(current.strip())

            ret = list(ret)
            ret.sort(key=lambda x: difflib.SequenceMatcher(None, x, current).ratio(), reverse=True)

            if len(split) == 2:
                ret = list(split[0] + "," + res for res in ret)

            await interaction.response.send_autocomplete(ret[:25])

        c_single.__doc__ = func.__doc__
        c_mixin.__doc__ = func.__doc__

        c_single = commands.group(name=name, invoke_without_command=True)(c_single)
        c_mixin = c_single.command(name="mixin")(c_mixin)

        inspect.currentframe().f_back.f_locals[f"_command_c{name}_single"] = c_single
        inspect.currentframe().f_back.f_locals[f"_command_c{name}_mixin"] = c_mixin

        inspect.currentframe().f_back.f_locals[f"_command_s{name}"] = s_command

    return wrapper


async def execute_scene(resp: CommandInterop, scene) -> typing.Union[typing.Tuple[None, None],
                                                                     typing.Tuple[BytesIO, float]]:
    execution_chunk = resp.chunk()

    loop = asyncio.get_running_loop()
    await execution_chunk.set("Rendering Image...")

    can_send = True

    async def update(io: BytesIO, t):
        nonlocal can_send

        mb = len(io.getbuffer()) / 1024 / 1024
        bar_size = int(mb / 8 * 20)
        details = [
            f"Size: {round(mb, 4)}MB `[{bar_size * '▓' + (20 - bar_size) * '░'}]`",
            f"Frame Second: {round(t, 2)}s"
        ]
        d = '\n'.join('    ' + detail for detail in details)

        await execution_chunk.set(f"Rendering Image...\n{d}")

    def callback(io, t):
        nonlocal can_send

        if can_send:
            can_send = False
            loop.create_task(update(io, t))
            loop.call_later(1, deexhaust)

        return len(io.getbuffer()) / 1024 / 1024 < 8

    def deexhaust():
        nonlocal can_send
        can_send = True

    future = execute(run_scene, scene, callback=callback)

    try:
        ret = await future

    except RuntimeError:
        await execution_chunk.set("File has grown too big")
        scene.cleanup_objects()
        return None, None

    else:
        execution_chunk.remove()
        return ret
