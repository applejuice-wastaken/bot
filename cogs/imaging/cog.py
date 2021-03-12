import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from io import BytesIO
import os

import discord
from PIL import Image

import aiohttp
from discord.ext import commands

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

def generic_flag_command(name):
    def wrapper(func):
        func = image_as_io(func)

        @commands.command(name=name)
        async def command(self, ctx, *, label_name):
            if ":" in label_name:
                chunks = label_name.split(":")
                ret = await url_from_name(chunks[1], chunks[0])
            else:
                ret = await url_from_name(label_name)

            if ret is None:
                await ctx.send("I don't know what is that")
            else:
                flag_url, flag_name, descriptor = ret
                await ctx.send(f"{descriptor} gave me a `{flag_name}` flag, "
                               f"unsure if that's what you want but I'll render it anyways")
                flag_bin = await retrieve(flag_url)
                user_bin = await ctx.author.avatar_url_as().read()
                io = await self.loop.run_in_executor(self.process_pool, partial(func, self, user_bin, flag_bin))
                await ctx.send(file=discord.File(io, "output.png"))

        return command

    return wrapper

class Imaging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop = asyncio.get_event_loop()

        self.process_pool = ThreadPoolExecutor(2)

        self.cooldown_mapping = commands.CooldownMapping.from_cooldown(1, 10.0, commands.BucketType.user)

    async def cog_before_invoke(self, ctx):
        bucket = self.cooldown_mapping.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(10, retry_after)

    @generic_flag_command("flag")
    def flag_executor(self, user_bin, flag_bin):
        user = Image.open(BytesIO(user_bin))
        flag = Image.open(BytesIO(flag_bin)).resize(user.size)
        edge = Image.open(asset_path("profile_edge.png")).resize(user.size).convert('L')

        output = Image.composite(flag, user, edge)

        return output

    @generic_flag_command("overlay")
    def overlay_executor(self, user_bin, flag_bin):
        user = Image.open(BytesIO(user_bin))
        flag = Image.open(BytesIO(flag_bin)).resize(user.size)
        mask = Image.new('L', user.size, 128)

        output = Image.composite(flag, user, mask)

        return output

def setup(bot):
    bot.add_cog(Imaging(bot))
