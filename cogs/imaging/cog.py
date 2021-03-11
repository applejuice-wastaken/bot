import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from io import BytesIO
import os

import discord
from PIL import Image

import aiohttp
from discord.ext import commands

async def retrieve(url):
    async with aiohttp.request("GET", url) as image_response:
        return await image_response.read()

async def search_wiki_and_retrieve_flag(flag_name):
    async with aiohttp.request("GET", f"https://lgbta.wikia.org/api.php?action=query&"
                                      f"list=search&srsearch={flag_name}&format=json") as search_response:
        json_content = await search_response.json()
        pages = json_content["query"]["search"]

        if pages:
            # there's results; get article image
            first_page_id = pages[0]["pageid"]

            async with aiohttp.request("GET", f"https://lgbta.wikia.org/api.php?action=imageserving&"
                                              f"wisId={first_page_id}&format=json") as image_response:
                json_content = await image_response.json()

                return json_content["image"]["imageserving"], pages[0]["title"]

    return None, None

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
        async def command(self, ctx, label_name):
            flag_url, flag_name = await search_wiki_and_retrieve_flag(label_name)
            if flag_url is None:
                await ctx.send("I don't know what is that")
            else:
                await ctx.send(f"LGBT wiki gave me a `{flag_name}` flag, "
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

    @generic_flag_command("flag")
    def flag_executor(self, user_bin, flag_bin):
        user = Image.open(BytesIO(user_bin))
        flag = Image.open(BytesIO(flag_bin)).resize(user.size)
        edge = Image.open(asset_path("profile_edge.png")).resize(user.size).convert('L')

        output = Image.composite(flag, user, edge)

        return output

    @generic_flag_command("overlay")
    def flag_executor(self, user_bin, flag_bin):
        user = Image.open(BytesIO(user_bin))
        flag = Image.open(BytesIO(flag_bin)).resize(user.size)
        mask = Image.new('L', user.size, 128)

        output = Image.composite(flag, user, mask)

        return output

def setup(bot):
    bot.add_cog(Imaging(bot))
