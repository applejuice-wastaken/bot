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
    async def on_message_delete(self, message):
        raw = [(idx, item) for idx, item in enumerate(self._uninvokers) if item.message.id == message.id]
        if len(raw) == 0:
            return

        index, item = raw[0]

        await discord.utils.maybe_coroutine(item.action)

        self._uninvokers.remove(item)


class UnloadEntry(namedtuple("UnloadEntry", "message action")):
    def __getattr__(self, item):
        return getattr(self.actions, item)


def setup(bot):
    bot.add_cog(Uninvoke(bot))
