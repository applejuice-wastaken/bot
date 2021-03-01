from abc import ABC
from typing import Dict, Any

import discord
from discord.ext import commands

from reactive_message.HoistedReactiveMessage import HoistedReactiveMessage
from reactive_message.ReactiveMessage import ReactiveMessage
from reactive_message.RoutedReactiveMessage import RoutedReactiveMessage, Route, Page


class TestReactiveMessageBasis:
    ONE = "\u0031\ufe0f\u20e3"
    TWO = "\u0032\ufe0f\u20e3"
    THREE = "\u0033\ufe0f\u20e3"
    FOUR = "\u0034\ufe0f\u20e3"
    FIVE = "\u0035\ufe0f\u20e3"

    def __init__(self):
        self.reactions = False
        self.show_embed = False
        self.change_content = False

    def generate_embed(self):
        return discord.Embed(title="This command tests the reactive_message module and it's updatability",
                             description="This module is capable of constructing classes that can render "
                                         "a message without any interfacing with discord")

    def render_message(self) -> Dict[str, Any]:
        if self.reactions:
            reactions = (self.ONE, self.TWO, self.THREE, self.FOUR, self.FIVE)
        else:
            reactions = ()

        if self.show_embed:
            embed = self.generate_embed()
        else:
            embed = None

        if self.change_content:
            content = "hey"
        else:
            content = "reactions :p"

        return dict(reactions=reactions, embed=embed, content=content)

    async def on_reaction_add(self, reaction, _):
        if reaction.emoji == self.ONE:
            self.reactions = not self.reactions
        elif reaction.emoji == self.TWO:
            self.show_embed = not self.show_embed
        elif reaction.emoji == self.THREE:
            self.change_content = not self.change_content
        else:
            return False
        return True


class TestReactiveMessage(TestReactiveMessageBasis, ReactiveMessage):
    def __init__(self, bot, channel):
        ReactiveMessage.__init__(self, bot, channel)
        TestReactiveMessageBasis.__init__(self)


class TestReactiveMessageHoist(TestReactiveMessageBasis, HoistedReactiveMessage):
    def __init__(self, bot, channel):
        HoistedReactiveMessage.__init__(self, bot, channel)
        TestReactiveMessageBasis.__init__(self)

    def generate_embed(self):
        return discord.Embed(title="This command tests the reactive_message module and it's updatability\n"
                                   "It also tests the hoist capability of this module",
                             description="This module is capable of constructing classes that can "
                                         "render a message without any interfacing with discord")


class RoutePage(Page):
    def render_message(self) -> Dict[str, Any]:
        embed = discord.Embed(description="This command tests the routing capability of the reactive_message module")

        embed.add_field(name="Map",
                        value="Root\n├Page 'a'\n├Page 'b'\n│├(Base Page)\n│└(Fallback Page)\n└(Fallback Page)")

        return dict(content="Route page", embed=embed)

    async def process_message(self, message):
        if len(message.content) == 1:
            self.message.route = message.content
            return True


class SubPage(Page, ABC):
    async def process_message(self, message):
        if message.content == "back":
            self.message.route = ""
            return True


class APage(SubPage):
    def render_message(self) -> Dict[str, Any]:
        return dict(content="Page A! (type back to go back to root)",
                    reactions=(self.message.ONE, self.message.TWO, self.message.FIVE))


class BPage(SubPage):
    def render_message(self) -> Dict[str, Any]:
        return dict(content="Woah page B! (type back to go back to root or something else idk)",
                    reactions=(self.message.ONE, self.message.TWO, self.message.FIVE))

    async def process_message(self, message):
        await super(BPage, self).process_message(message)
        if message.content != "back":
            self.message.route = f"b.{message.content[:10]}"
            return True


class RestPage(SubPage):
    def render_message(self) -> Dict[str, Any]:
        return dict(content=f"Page named {self.message['n']}\n"
                            f"(route: {self.message.route})",
                    reactions=(self.message.ONE, self.message.FIVE, self.message.TWO))


class TestRouteReactiveMessage(RoutedReactiveMessage):
    ONE = "\u0031\ufe0f\u20e3"
    TWO = "\u0032\ufe0f\u20e3"
    THREE = "\u0033\ufe0f\u20e3"
    FOUR = "\u0034\ufe0f\u20e3"
    FIVE = "\u0035\ufe0f\u20e3"
    ROUTE = (Route()
             .add_route("a", APage)
             .add_route("b", Route()
                        .add_fallback("n", RestPage)
                        .base(BPage))
             .add_fallback("n", RestPage)
             .base(RoutePage))


class FeatureTester(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="reactive-menu")
    async def rm(self, ctx):
        TestReactiveMessage(self.bot, ctx.channel)

    @commands.command(name="reactive-menu-hoist")
    async def rmh(self, ctx):
        TestReactiveMessageHoist(self.bot, ctx.channel)

    @commands.command(name="reactive-menu-route")
    async def rmr(self, ctx):
        TestRouteReactiveMessage(self.bot, ctx.channel)


def setup(bot):
    bot.add_cog(FeatureTester(bot))
