import asyncio
import datetime
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from io import BytesIO

import aiohttp
import nextcord
from PIL import Image, ImageStat
from nextcord.ext import commands

from .command import generic_flag_command, stitch_flags
from .executor import execute
from .flag_retriever.flag import Flag
from .resize import center_resize
from .scenery import FlagOverlayScene


async def retrieve(url):
    async with aiohttp.request("GET", url) as image_response:
        return await image_response.read()


def to_io(image):
    output_buffer = BytesIO()
    image.save(output_buffer, "PNG")
    output_buffer.seek(0)
    return output_buffer


def asset_path(name):
    self_dir = os.path.dirname(__file__)
    return os.path.join(self_dir, 'assets', name)


class BadImageInput(Exception):
    pass


def find_mean_color(image):
    if not isinstance(image, Image.Image):
        image = Image.open(BytesIO(image))

    image = image.convert("RGB")

    stat = ImageStat.Stat(image)

    return [int(i) for i in stat.median]


class Imaging(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.loop = asyncio.get_event_loop()

        self.cooldown_mapping = commands.CooldownMapping.from_cooldown(1, 20.0, commands.BucketType.user)
        self.execution_semaphore = asyncio.Semaphore(2)

    async def cog_before_invoke(self, ctx):
        bucket = self.cooldown_mapping.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(bucket, bucket.per, commands.BucketType.user)

    @generic_flag_command("circle")
    def flag_executor(self, user, flag, *, rotate, fps):
        """retrieves a flag and returns your profile picture with it in the edge"""
        flag = center_resize(flag, *user.size)
        edge = Image.open(asset_path("profile_edge.png")).resize(user.size).convert('L')

        return FlagOverlayScene(user, edge, flag, rotate=rotate, fps=fps)

    @generic_flag_command("overlay")
    def overlay_executor(self, user, flag, *, rotate, fps):
        """retrieves a flag and overlays it over your profile picture"""
        flag = center_resize(flag, *user.size)
        flag = flag.resize((int(flag.size[0] * 1.5), int(flag.size[1] * 1.5)))
        mask = Image.new('L', user.size, 128)

        return FlagOverlayScene(user, mask, flag, rotate=rotate, fps=fps)

    @commands.group(name="flag", invoke_without_command=True)
    async def show_flag(self, ctx: commands.Context, *, flag: Flag):
        """shows a flag"""
        async with ctx.typing():
            opened_flag = await flag.open()
            pix = await execute(find_mean_color, opened_flag)

            io = await execute(to_io, opened_flag)

            file = nextcord.File(io, filename="v.png")

            e = nextcord.Embed(color=nextcord.Color.from_rgb(*pix[:3]))
            e.set_image(url="attachment://v.png")
            await ctx.send(f"`{flag.name}`, provided by {flag.provider}", file=file, embed=e)

    @show_flag.command(name="mixin")
    async def mixin(self, ctx, *flags: Flag):
        async with ctx.typing():
            if len(flags) == 0:
                await ctx.send(f"no flags provided")
                return

            listing = "\n".join(f"    `{flag.name}` flag provided by {flag.provider}" for flag in flags)

            if len(flags) < 2:
                await ctx.send(f"insufficient flags:\n{listing}")
                return

            opened_flags = []
            flags_url = {}

            for flag in flags:
                if flag.url in flags_url:
                    opened_flags.append(flags_url[flag.url])
                else:
                    image = await flag.open()
                    opened_flags.append(image)
                    flags_url[flag.url] = image

            try:
                stitched_flag = await execute(stitch_flags, opened_flags[0].size, *opened_flags)

                pix = await execute(find_mean_color, stitched_flag)

                # little hack to avoid writing function
                io = await execute(to_io, stitched_flag)
            except BadImageInput:
                await ctx.send(f"This flag type is unsupported")
            else:
                file = nextcord.File(io, filename="v.png")
                e = nextcord.Embed(color=nextcord.Color.from_rgb(*pix))
                e.set_image(url="attachment://v.png")
                await ctx.send(f"using:\n{listing}", file=file, embed=e)

    @commands.command(name="avatar", aliases=("pfp",))
    async def avatar(self, ctx, target: nextcord.User = None):
        target = ctx.author if target is None else target

        asset = target.avatar_url_as()
        user_bin = await asset.read()

        try:
            pix = await execute(find_mean_color, user_bin)
        except BadImageInput:
            # given that it's from nextcord, it should not come here
            # because pillow would theoretically support it
            pix = (0, 0, 0)

        embed = nextcord.Embed(color=nextcord.Color.from_rgb(*pix))
        embed.set_image(url=str(asset))
        await ctx.send(f"{target.mention}'s profile picture", embed=embed,
                       mention_author=nextcord.AllowedMentions.none())


def time_until_end_of_day(dt=None):
    if dt is None:
        dt = datetime.datetime.now()
    tomorrow = dt + datetime.timedelta(days=1)
    return datetime.datetime.combine(tomorrow, datetime.time.min) - dt
