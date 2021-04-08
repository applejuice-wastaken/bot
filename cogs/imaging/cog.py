import asyncio
import inspect
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from io import BytesIO
import os

import discord
from PIL import Image, ImageStat

import aiohttp
from PIL.ImageDraw import ImageDraw
from discord.ext import commands

from .flag_retriever.flag import Flag

import math

import colorsys


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


def open_flags(*flags_bin):
    ret = []

    try:
        for flag in flags_bin:
            ret.append(Image.open(BytesIO(flag)))
    except Image.UnidentifiedImageError as e:
        raise BadImageInput from e

    return ret[0] if len(ret) == 1 else ret

def stitch_flags(size, *flags: Image):
    mask = Image.new("L", size, 0)
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    ret = Image.new("RGB", size, (0, 0, 0))

    drawer = ImageDraw(mask)
    overlay_drawer = ImageDraw(overlay)

    step_size = math.pi * 2 / len(flags)
    point_offset = max(size) * 2
    angle_offset = -math.pi / 2  # begin at the top

    for idx, flag in enumerate(flags):
        start = (math.cos(idx * step_size - angle_offset) * point_offset + size[0] / 2,
                 math.sin(idx * step_size - angle_offset) * point_offset + size[1] / 2)

        middle = (math.cos((idx + 0.5) * step_size - angle_offset) * point_offset + size[0] / 2,
                  math.sin((idx + 0.5) * step_size - angle_offset) * point_offset + size[1] / 2)

        end = (math.cos((idx + 1) * step_size - angle_offset) * point_offset + size[0] / 2,
               math.sin((idx + 1) * step_size - angle_offset) * point_offset + size[1] / 2)

        # quick and dirty way of drawing only a part of the mask

        drawer.polygon((size[0] / 2, size[1] / 2) + start + middle + end, 255)

        overlay_drawer.line((size[0] / 2, size[1] / 2) + start, (255, 255, 255, 255), 15)
        overlay_drawer.line((size[0] / 2, size[1] / 2) + end, (255, 255, 255, 255), 15)

        overlay_drawer.line((size[0] / 2, size[1] / 2) + start, (0, 0, 0, 255), 5)
        overlay_drawer.line((size[0] / 2, size[1] / 2) + end, (0, 0, 0, 255), 5)

        flag = center_resize(flag, *size)

        ret.paste(flag, mask=mask)

        drawer.rectangle((0, 0) + mask.size, 0)  # clear

    # fixing center part where the lines just overlap

    for idx in range(len(flags)):
        point = (math.cos(idx * step_size - angle_offset) * point_offset + size[0] / 2,
                 math.sin(idx * step_size - angle_offset) * point_offset + size[1] / 2)

        overlay_drawer.line((size[0] / 2, size[1] / 2) + point, (0, 0, 0, 255), 5)

    ret.paste(overlay, mask=overlay)

    return ret


def generic_flag_command(name):
    def wrapper(func):
        func = image_as_io(func)

        async def command(self, ctx, *, flag: Flag):
            print("normal")
            self: Imaging

            await ctx.send(f"using `{flag.name}` flag provided by {flag.provider}")

            flag_bin = await flag.read()
            user_bin = await ctx.author.avatar_url_as().read()

            try:
                flag = await self.execute(open_flags, flag_bin)
                user = await self.execute(open_flags, user_bin)

                io = await self.execute(func, self, user, flag)

            except BadImageInput:
                await ctx.send(f"This flag type is unsupported")
            else:
                await ctx.send(file=discord.File(io, "output.png"))

        async def mixin(self, ctx, *flags: Flag):
            if len(flags) == 0:
                await ctx.send(f"no flags provided")
                return

            listing = "\n".join(f"    `{flag.name}` flag provided by {flag.provider}" for flag in flags)

            if len(flags) < 2:
                await ctx.send(f"insufficient flags:\n{listing}")
                return

            await ctx.send(f"using:\n{listing}")

            flags_bin = []
            for flag in flags:
                flags_bin.append(await flag.read())

            user_bin = await ctx.author.avatar_url_as().read()

            try:
                flags = await self.execute(open_flags, *flags_bin)
                user = await self.execute(open_flags, user_bin)

                stitched_flag = await self.execute(stitch_flags, user.size, *flags)

                io = await self.execute(func, self, user, stitched_flag)

            except BadImageInput:
                await ctx.send(f"This flag type is unsupported")
            else:
                await ctx.send(file=discord.File(io, "output.png"))

        command.__doc__ = func.__doc__
        mixin.__doc__ = func.__doc__

        c = commands.group(name=name, invoke_without_command=True)(command)

        inspect.currentframe().f_back.f_locals[f"_command_{name}_mixin"] = c.command(name="mixin")(mixin)

        return c

    return wrapper

def center_resize(target: Image.Image, width, height):
    scale = max(width / target.width, height / target.height)

    new_width = target.width * scale
    new_height = target.height * scale

    x = (new_width - width) / 2
    y = (new_height - height) / 2

    box = [int(i) for i in (x, y, x + width, y + height)]

    return target.resize((int(new_width), int(new_height))).crop(box)


def find_mean_color(image):
    if not isinstance(image, Image.Image):
        image = Image.open(BytesIO(image)).convert("RGB")

    stat = ImageStat.Stat(image)

    return [int(i) for i in stat.median]


class Imaging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop = asyncio.get_event_loop()

        self.process_pool = ThreadPoolExecutor(2)

        self.cooldown_mapping = commands.CooldownMapping.from_cooldown(1, 5.0, commands.BucketType.user)

    async def cog_before_invoke(self, ctx):
        bucket = self.cooldown_mapping.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(bucket.per, retry_after)

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

    @commands.command(name="flag")
    async def show_flag_only(self, ctx, *, flag: Flag):
        """shows a flag"""
        flag_bin = await flag.read()

        try:
            pix = await self.loop.run_in_executor(self.process_pool, partial(find_mean_color, flag_bin))
        except Image.UnidentifiedImageError:
            await ctx.send(f"`{flag.name}` type, provided by {flag.provider}, is unsupported")
        else:
            if flag.is_remote:
                embed = discord.Embed(color=discord.Color.from_rgb(*pix))
                embed.set_image(url=flag.url)
                await ctx.send(f"`{flag.name}`, provided by {flag.provider}", embed=embed)
            else:
                file = discord.File(flag.url, filename="v.png")
                e = discord.Embed(color=discord.Color.from_rgb(*pix))
                e.set_image(url="attachment://v.png")
                await ctx.send(f"`{flag.name}`, provided by {flag.provider}", file=file, embed=e)

    def execute(self, func, *args, **kwargs):
        return self.loop.run_in_executor(self.process_pool, partial(func, *args, **kwargs))