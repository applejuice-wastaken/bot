from __future__ import annotations

from io import BytesIO

import aiohttp
from discord.ext import commands

import aiofiles

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

    @classmethod
    async def convert(cls, ctx, argument) -> Flag:
        from cogs.imaging.flag_retriever import get_flag

        if ":" in argument:
            chunks = argument.split(":")
            ret = await get_flag(chunks[1], chunks[0])
        else:
            ret = await get_flag(argument)

        if ret is None:
            raise commands.BadArgument("Flag not found.")

        return ret
