import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from io import BytesIO
import os

import discord
from PIL import Image, ImageStat

import aiohttp
from discord.ext import commands

from .flag_retriever.flag import Flag


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


def generic_flag_command(name):
    def wrapper(func):
        func = image_as_io(func)

        async def command(self, ctx, *, flag: Flag):
            await ctx.send(f"using `{flag.name}` flag provided by {flag.provider}")

            flag_bin = await flag.read()
            user_bin = await ctx.author.avatar_url_as().read()

            try:
                io = await self.loop.run_in_executor(self.process_pool, partial(opener, self, user_bin, flag_bin))
            except BadImageInput:
                await ctx.send(f"This flag type is unsupported")
            else:
                await ctx.send(file=discord.File(io, "output.png"))

        def opener(self, user_bin, flag_bin):
            user = Image.open(BytesIO(user_bin))
            flag = None
            try:
                flag = Image.open(BytesIO(flag_bin))
            except Image.UnidentifiedImageError as e:
                raise BadImageInput from e
            else:
                return func(self, user, flag)
            finally:
                user.close()

                if flag is not None:
                    flag.close()

        command.__doc__ = func.__doc__

        return commands.command(name=name)(command)

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
            pix = await self.loop.run_in_executor(self.process_pool, partial(self.find_mean_color, flag_bin))
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

    def find_mean_color(self, flag_bin):
        img = Image.open(BytesIO(flag_bin)).convert("RGB")
        stat = ImageStat.Stat(img)

        return [int(i) for i in stat.median]
