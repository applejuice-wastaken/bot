from collections import deque, namedtuple

import discord
from discord.ext import commands


class Uninvoke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._uninvokers = deque(maxlen=100)

    def create_unload(self, message, unloader):
        entry = UnloadEntry(message, unloader)
        self._uninvokers.append(entry)
        return entry

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return

        unloader = discord.utils.get(self._uninvokers, message__id=after.id)

        if unloader is not None:
            await discord.utils.maybe_coroutine(unloader.action)

            self._uninvokers.remove(unloader)

        await self.bot.process_commands(after)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        unloader = discord.utils.get(self._uninvokers, message__id = message.id)

        if unloader is not None:
            await discord.utils.maybe_coroutine(unloader.action)

            self._uninvokers.remove(unloader)


UnloadEntry = namedtuple("UnloadEntry", "message action")


def setup(bot):
    bot.add_cog(Uninvoke(bot))
