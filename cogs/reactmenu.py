from typing import Type

import discord
from discord.ext import commands

from reactive_message.ReactiveMessage import ReactiveMessage


class ReactMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.react_menus = []

    async def instantiate_new(self, cls, channel, *args, **kwargs):
        new_instance = cls(self, channel, *args, **kwargs)
        self.react_menus.append(new_instance)
        await new_instance.send()
        return new_instance

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        for menu in self.react_menus:
            if menu.bound_message.id == message.id:
                await menu.remove()
                return

    @commands.Cog.listener()
    async def on_message(self, message):
        for menu in self.react_menus:
            if menu.channel == message.channel:
                await menu.process_message(message)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        for menu in self.react_menus:
            if menu.bound_message.id == reaction.message.id and user != self.bot.user:
                await menu.process_reaction_add(reaction, user)
                return

def setup(bot):
    bot.add_cog(ReactMenu(bot))
