import asyncio
import datetime
import inspect
import os
import typing
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from io import BytesIO

import aiohttp
import nextcord
from PIL import Image, ImageStat
from PIL.ImageDraw import ImageDraw
from nextcord.ext import commands

from .flag_retriever.flag import Flag
from .resize import center_resize


async def retrieve(url):
    async with aiohttp.request("GET", url) as image_response:
        return await image_response.read()


def image_as_io(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        pil_image = func(*args, **kwargs)
        output_buffer = BytesIO()
        pil_image.save(output_buffer, "PNG")
        output_buffer.seek(0)
        return output_buffer

    return wrapper


def asset_path(name):
    self_dir = os.path.dirname(__file__)
    return os.path.join(self_dir, 'assets', name)


class BadImageInput(Exception):
    pass


def stitch_flags(size, *flags: Image):
    mask = Image.new("L", size, 0)
    ret = Image.new("RGB", size, (0, 0, 0))

    mask_drawer = ImageDraw(mask)

    spacing = 1 / (len(flags) - 1) * size[0]

    def generate_point_for_idx(index):
        return index * spacing, size[1] if index % 2 == 0 else 0

    for idx, flag in enumerate(flags):
        points = [*generate_point_for_idx(idx - 1), *generate_point_for_idx(idx), *generate_point_for_idx(idx + 1)]

        mask_drawer.polygon(points, 255)

        flag = center_resize(flag, *size)

        ret.paste(flag, mask=mask)

        mask_drawer.rectangle((0, 0) + mask.size, 0)  # clear

    return ret


async def try_get_image(ctx: commands.Context, user: typing.Optional[nextcord.Member]):
    if user is not None:
        return await user.avatar.read()

    if ctx.message.reference is None:
        target = ctx.message
    else:
        target = await ctx.channel.fetch_message(ctx.message.reference.message_id)

    target: nextcord.Message

    if target.attachments:
        return await target.attachments[0].read()

    else:
        return await target.author.avatar.read()


def generic_flag_command(name):
    def wrapper(func):
        func = image_as_io(func)

        async def command(self, ctx, user: typing.Optional[nextcord.Member], *, flag: Flag):
            self: Imaging

            await ctx.send(f"using `{flag.name}` flag provided by {flag.provider}")

            async with ctx.typing():
                flag = await flag.open()

                user_bin = await try_get_image(ctx, user)

                try:
                    user = await self.execute(Image.open, BytesIO(user_bin))

                    io = await self.execute(func, self, user, flag)

                except BadImageInput:
                    await ctx.send(f"This flag type is unsupported")
                else:
                    await ctx.send(file=nextcord.File(io, "output.png"))

        async def mixin(self, ctx, user: typing.Optional[nextcord.Member], *flags: Flag):
            if len(flags) == 0:
                await ctx.send(f"no flags provided")
                return

            listing = "\n".join(f"    `{flag.name}` flag provided by {flag.provider}" for flag in flags)

            if len(flags) < 2:
                await ctx.send(f"insufficient flags:\n{listing}")
                return

            await ctx.send(f"using:\n{listing}")

            async with ctx.typing():
                opened_flags = []
                flags_url = {}

                for flag in flags:
                    if flag.url in flags_url:
                        opened_flags.append(flags_url[flag.url])
                    else:
                        image = await flag.open()
                        opened_flags.append(image)
                        flags_url[flag.url] = image

                user_bin = await try_get_image(ctx, user)

                try:
                    user = await self.execute(Image.open, BytesIO(user_bin))

                    stitched_flag = await self.execute(stitch_flags, user.size, *opened_flags)

                    io = await self.execute(func, self, user, stitched_flag)

                except BadImageInput:
                    await ctx.send(f"This flag type is unsupported")
                else:
                    await ctx.send(file=nextcord.File(io, "output.png"))

        command.__doc__ = func.__doc__
        mixin.__doc__ = func.__doc__

        c = commands.group(name=name, invoke_without_command=True)(command)

        inspect.currentframe().f_back.f_locals[f"_command_{name}_mixin"] = c.command(name="mixin")(mixin)

        return c

    return wrapper


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

        self.process_pool = ThreadPoolExecutor(2)

        self.cooldown_mapping = commands.CooldownMapping.from_cooldown(1, 5.0, commands.BucketType.user)

    async def cog_before_invoke(self, ctx):
        bucket = self.cooldown_mapping.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(bucket, bucket.per, commands.BucketType.user)

    @generic_flag_command("circle")
    def flag_executor(self, user, flag):
        """retrieves a flag and returns your profile picture with it in the edge"""
        flag = center_resize(flag, *user.size)
        edge = Image.open(asset_path("profile_edge.png")).resize(user.size).convert('L')

        output = Image.composite(flag, user, edge)

        return output

    @generic_flag_command("overlay")
    def overlay_executor(self, user, flag):
        """retrieves a flag and overlays it over your profile picture"""
        flag = center_resize(flag, *user.size)
        mask = Image.new('L', user.size, 128)

        output = Image.composite(flag, user, mask)

        return output

    @commands.group(name="flag", invoke_without_command=True)
    async def show_flag(self, ctx: commands.Context, *, flag: Flag):
        """shows a flag"""
        async with ctx.typing():
            opened_flag = await flag.open()
            pix = await self.execute(find_mean_color, opened_flag)

            io = await self.execute(image_as_io(lambda sf: sf), opened_flag)

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
                stitched_flag = await self.execute(stitch_flags, opened_flags[0].size, *opened_flags)

                pix = await self.execute(find_mean_color, stitched_flag)

                # little hack to avoid writing function
                io = await self.execute(image_as_io(lambda sf: sf), stitched_flag)
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
            pix = await self.execute(find_mean_color, user_bin)
        except BadImageInput:
            # given that it's from nextcord, it should not come here
            # because pillow would theoretically support it
            pix = (0, 0, 0)

        embed = nextcord.Embed(color=nextcord.Color.from_rgb(*pix))
        embed.set_image(url=str(asset))
        await ctx.send(f"{target.mention}'s profile picture", embed=embed,
                       mention_author=nextcord.AllowedMentions.none())

    def execute(self, func, *args, **kwargs):
        return self.loop.run_in_executor(self.process_pool, partial(func, *args, **kwargs))


def time_until_end_of_day(dt=None):
    if dt is None:
        dt = datetime.datetime.now()
    tomorrow = dt + datetime.timedelta(days=1)
    return datetime.datetime.combine(tomorrow, datetime.time.min) - dt
