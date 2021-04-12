import asyncio
import datetime

from collections import deque
import dataclasses

import discord
from discord.ext import commands

@dataclasses.dataclass(frozen=True)
class Record:
    message_id: int
    deleted_messages: int = 0


class Moderation(commands.Cog):
    DOWN = "\U0001f53d"
    UP = "\U0001f53c"

    def __init__(self, bot):
        self.bot = bot

        self.purge_info: deque[Record] = deque(maxlen=30)

    async def purge_action(self, ctx, messages: list):
        messages.sort(key=lambda value: value.id, reverse=True)

        for message in messages:
            age = datetime.datetime.now() - message.created_at
            if age.days > 14:
                await ctx.send("No can do; there's messages older than 14 days", delete_after=10)
                await ctx.message.delete(delay=10)
                break

        else:
            def check(ev):
                return ev.user_id == ctx.author.id

            confirm_message = await ctx.send(f"This will delete {len(messages)} messages, are you sure?")

            if messages[0].id != ctx.message.id:
                await messages[0].add_reaction(self.UP)

            await messages[-1].add_reaction(self.DOWN)

            try:
                emoji = await self.bot.choice(confirm_message, "✅", "❌", check=check)
            except asyncio.TimeoutError:
                await ctx.send("Timeout", delete_after=10)
                await ctx.message.delete(delay=5)
                await confirm_message.delete(delay=5)
            else:
                if emoji.name == "✅":
                    deleted = 0
                    for message in messages:
                        info = discord.utils.find(lambda other: other.message_id == message.id, self.purge_info)
                        if info is not None:
                            deleted += info.deleted_messages
                        deleted += 1

                    while len(messages) > 0:
                        await ctx.channel.delete_messages(messages[:101])
                        messages = messages[101:]

                    trace = await ctx.send(f"*[Deleted {deleted} Messages]*")

                    self.purge_info.append(Record(trace.id, deleted))
                else:
                    await ctx.message.delete()

                    if messages[0].id != ctx.message.id:
                        await messages[0].remove_reaction(self.UP, ctx.guild.me)

                    await messages[-1].remove_reaction(self.DOWN, ctx.guild.me)

                await confirm_message.delete()

    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.command()
    async def purge_until(self, ctx, message_id: int):
        """purges messages until message_id"""
        messages = await ctx.channel.history(limit=1000, after=discord.Object(message_id)).flatten()

        if len(messages) <= 1:
            await ctx.send("Insufficient amount of messages")
        else:
            await self.purge_action(ctx, messages)

    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.command()
    async def purge(self, ctx, quantity: int):
        """purges an amount of messages sorted by newest"""
        if quantity <= 1:
            await ctx.send("Has to be higher than 1")
        else:
            messages = await ctx.channel.history(limit=quantity).flatten()

            await self.purge_action(ctx, messages)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        info = discord.utils.find(lambda other: other.message_id == message.id, self.purge_info)

        if info:
            self.purge_info.remove(info)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        for message in messages:
            info = discord.utils.find(lambda other: other.message_id == message.id, self.purge_info)

            if info:
                self.purge_info.remove(info)


def setup(bot):
    bot.add_cog(Moderation(bot))
