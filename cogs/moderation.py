import asyncio
import datetime
import time

import discord
from discord.ext import commands


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_state = {}
        self.game_instances = []
        self.play_list = {}

    async def purge_action(self, ctx, messages):
        for message in messages:
            age = datetime.datetime.now() - message.created_at
            if age.days > 14:
                await ctx.send("No can do; there's messages older than 14 days", delete_after=10)
                await ctx.message.delete(delay=10)
                break
        else:
            def check(r, u):
                return u.id == ctx.author.id

            message = await ctx.send(f"This will delete {len(messages)} messages, are you sure?")
            try:
                reaction, user = await self.bot.choice(message, "✅", "❌", check=check)
            except asyncio.TimeoutError:
                await ctx.send("Timeout", delete_after=10)
                await ctx.message.delete(delay=5)
                await message.delete(delay=5)
            else:
                if reaction.emoji == "✅":
                    await ctx.channel.delete_messages(messages)
                else:
                    await ctx.message.delete()

                await message.delete()

    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.command()
    async def purge_until(self, ctx, message_id: int):
        messages = await ctx.channel.history(limit=100, after=discord.Object(message_id)).flatten()

        await self.purge_action(ctx, messages)

    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.command()
    async def purge(self, ctx, quantity: int):
        messages = await ctx.channel.history(limit=quantity).flatten()

        await self.purge_action(ctx, messages)

def setup(bot):
    bot.add_cog(Moderation(bot))
