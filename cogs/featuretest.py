from abc import ABC
from typing import Dict, Any

import discord
from discord.ext import commands

from reactive_message.HoistedReactiveMessage import HoistedReactiveMessage
from reactive_message.ReactiveMessage import ReactiveMessage
from reactive_message.RenderingProperty import RenderingProperty
from reactive_message.RoutedReactiveMessage import RoutedReactiveMessage, Route, Page


class TestReactiveMessageBasis:
    reactions = RenderingProperty("show_reactions")
    show_embed = RenderingProperty("show_embed")
    change_content = RenderingProperty("change_content")

    ONE = "\u0031\ufe0f\u20e3"
    TWO = "\u0032\ufe0f\u20e3"
    THREE = "\u0033\ufe0f\u20e3"
    FOUR = "\u0034\ufe0f\u20e3"
    FIVE = "\u0035\ufe0f\u20e3"

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


class TestReactiveMessage(TestReactiveMessageBasis, ReactiveMessage):
    pass


class TestReactiveMessageHoist(TestReactiveMessageBasis, HoistedReactiveMessage):
    def generate_embed(self):
        return discord.Embed(title="This command tests the reactive_message module and it's updatability\n"
                                   "It also tests the hoist capability of this module",
                             description="This module is capable of constructing classes that can "
                                         "render a message without any interfacing with discord")


class RoutePage(Page):
    def render_message(self, reactive_message, args: dict) -> Dict[str, Any]:
        embed = discord.Embed(description="This command tests the routing capability of the reactive_message module")

        embed.add_field(name="Map",
                        value="Root\n├Page 'a'\n├Page 'b'\n│├(Base Page)\n│└(Fallback Page)\n└(Fallback Page)")

        return dict(content="Route page", embed=embed)

    async def on_message(self, message, reactive_message, args: dict):
        if len(message.content) == 1:
            reactive_message.route = message.content


class SubPage(Page, ABC):
    async def on_message(self, message, reactive_message, args: dict):
        if message.content == "back":
            reactive_message.route = ""


class APage(SubPage):
    def render_message(self, reactive_message, args: dict) -> Dict[str, Any]:
        return dict(content="Page A! (type back to go back to root)",
                    reactions=(reactive_message.ONE, reactive_message.TWO, reactive_message.FIVE))


class BPage(SubPage):
    def render_message(self, reactive_message, args: dict) -> Dict[str, Any]:
        return dict(content="Woah page B! (type back to go back to root or something else idk)",
                    reactions=(reactive_message.ONE, reactive_message.TWO, reactive_message.FIVE))

    async def on_message(self, message, reactive_message, args: dict):
        await super(BPage, self).on_message(message, reactive_message, args)
        if message.content != "back":
            reactive_message.route = f"b.{message.content[:10]}"


class RestPage(SubPage):
    def render_message(self, reactive_message, args: dict) -> Dict[str, Any]:
        return dict(content=f"Page named {args['n']}\n"
                            f"(route: {reactive_message.route})",
                    reactions=(reactive_message.ONE, reactive_message.FIVE,
                               reactive_message.TWO))


class TestRouteReactiveMessage(RoutedReactiveMessage):
    ONE = "\u0031\ufe0f\u20e3"
    TWO = "\u0032\ufe0f\u20e3"
    THREE = "\u0033\ufe0f\u20e3"
    FOUR = "\u0034\ufe0f\u20e3"
    FIVE = "\u0035\ufe0f\u20e3"
    ROUTE = (Route()
             .add_route("a", APage())
             .add_route("b", Route()
                        .add_fallback("n", RestPage())
                        .base(BPage()))
             .add_fallback("n", RestPage())
             .base(RoutePage()))


class FeatureTester(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="reactive-menu")
    async def rm(self, ctx):
        await self.bot.get_cog("ReactMenu").instantiate_new(TestReactiveMessage, ctx.channel)

    @commands.command(name="reactive-menu-hoist")
    async def rmh(self, ctx):
        await self.bot.get_cog("ReactMenu").instantiate_new(TestReactiveMessageHoist, ctx.channel)

    @commands.command(name="reactive-menu-route")
    async def rmr(self, ctx):
        await self.bot.get_cog("ReactMenu").instantiate_new(TestRouteReactiveMessage, ctx.channel)


def setup(bot):
    bot.add_cog(FeatureTester(bot))
