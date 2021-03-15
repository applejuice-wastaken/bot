import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from io import BytesIO
import os

import discord
from PIL import Image, ImageStat

import aiohttp
from discord.ext import commands
from discord.ext.commands import Converter

from .flag_retreiver import url_from_name


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

class Flag:
    def __init__(self, url, name, provider):
        self.provider = provider
        self.name = name
        self.url = url

    @classmethod
    async def convert(cls, ctx, argument):
        if ":" in argument:
            chunks = argument.split(":")
            ret = await url_from_name(chunks[1], chunks[0])
        else:
            ret = await url_from_name(argument)

        if ret is None:
            raise commands.BadArgument("Flag not found.")
        else:
            flag_url, flag_name, provider = ret
            return Flag(url=flag_url, name=flag_name, provider=provider)


def generic_flag_command(name):
    def wrapper(func):
        func = image_as_io(func)

        @commands.command(name=name)
        async def command(self, ctx, *, flag_name: Flag):
            await ctx.send(f"using `{flag_name.name}` flag provided by {flag_name.provider}")
            flag_bin = await retrieve(flag_name.url)
            user_bin = await ctx.author.avatar_url_as().read()
            io = await self.loop.run_in_executor(self.process_pool, partial(func, self, user_bin, flag_bin))
            await ctx.send(file=discord.File(io, "output.png"))

        return command

    return wrapper

def center_resize(target: Image.Image, width, height):
    if target.width < target.height:
        # width is the smallest side
        new_width = width
        x = 0
        new_height = target.height * (new_width / target.width)
        y = (new_height - height) / 2
    else:
        # width is the smallest side
        new_height = height
        y = 0
        new_width = target.width * (new_height / target.height)
        x = (new_width - width) / 2

    box = [int(i) for i in (x, y, x + width, y + height)]

    return target.resize((int(new_width), int(new_height))).crop(box)

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
    def flag_executor(self, user_bin, flag_bin):
        user = Image.open(BytesIO(user_bin))
        flag = center_resize(Image.open(BytesIO(flag_bin)), *user.size)
        edge = Image.open(asset_path("profile_edge.png")).resize(user.size).convert('L')

        output = Image.composite(flag, user, edge)

        return output

    @generic_flag_command("overlay")
    def overlay_executor(self, user_bin, flag_bin):
        user = Image.open(BytesIO(user_bin))
        flag = center_resize(Image.open(BytesIO(flag_bin)), *user.size)
        mask = Image.new('L', user.size, 128)

        output = Image.composite(flag, user, mask)

        return output

    @commands.command(name="flag")
    async def show_flag_only(self, ctx, *, flag_name: Flag):
        flag_bin = await retrieve(flag_name.url)

        pix = await self.loop.run_in_executor(self.process_pool, partial(self.find_mean_color, flag_bin))

        embed = discord.Embed(color=discord.Color.from_rgb(*pix))
        embed.set_image(url=flag_name.url)
        await ctx.send(f"`{flag_name.name}`, provided by {flag_name.provider}", embed=embed)

    def find_mean_color(self, flag_bin):
        img = Image.open(BytesIO(flag_bin)).convert("RGB")
        stat = ImageStat.Stat(img)

        return [int(i) for i in stat.median]
