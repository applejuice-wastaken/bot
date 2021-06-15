from __future__ import annotations

import asyncio
from functools import partial
from io import BytesIO, StringIO

import aiohttp
from PIL import Image
from discord.ext import commands

import aiofiles
from reportlab.graphics import renderPM

from svglib.svglib import svg2rlg

class Flag:
    def __init__(self, url, name, provider, *, is_remote=False):
        self.is_remote = is_remote
        self.provider = provider
        self.name = name
        self.url = url

    async def read(self):
        if self.is_remote:
            obj = aiohttp.request("GET", self.url)
        else:
            obj = aiofiles.open(self.url, "rb")

        async with obj as reader:
            return await reader.read()

    async def open(self):
        data = await self.read()

        if data.startswith(b"<svg"):
            # maybe svg
            drawing = svg2rlg(StringIO(data.decode()))
            io = BytesIO()
            renderPM.drawToFile(drawing, io, fmt="PNG")
        else:
            # maybe raster image
            io = BytesIO(data)

        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(None, partial(Image.open, io))

    @classmethod
    async def convert(cls, ctx, argument) -> Flag:
        from cogs.imaging.flag_retriever import get_flag

        if ":" in argument:
            chunks = argument.split(":")
            ret = await get_flag(chunks[1], chunks[0])
        else:
            ret = await get_flag(argument)

        if ret is None:
            raise commands.BadArgument(f"Flag `{argument}` not found.")

        return ret
