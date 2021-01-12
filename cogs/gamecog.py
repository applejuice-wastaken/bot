from typing import List

import discord
from discord.ext import commands

from games.Game import Game, EndGame
from games.game_modules.uno import uno

games = {"uno": uno.UnoGame}


class GameCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_state = {}
        self.game_instances: List[Game] = []
        self.play_list = {}

    @commands.command()
    async def join(self, ctx):
        """Joins the queue for a game"""
        if ctx.guild.id not in self.play_list:
            self.play_list[ctx.guild.id] = []

        if ctx.author in self.play_list[ctx.guild.id]:
            await ctx.send("You're already in")
        elif ctx.author.id in self.user_state:
            await ctx.send("You're already occupied")
        else:
            self.play_list[ctx.guild.id].append(ctx.author)
            self.user_state[ctx.author.id] = ctx.guild.id
            await ctx.send(f"Ok we have {len(self.play_list[ctx.guild.id])} users now")

    @commands.command()
    async def leave(self, ctx):
        """Leaves the queue"""
        if ctx.guild.id not in self.play_list:
            self.play_list[ctx.guild.id] = []

        if ctx.author not in self.play_list[ctx.guild.id]:
            await ctx.send("You weren't in the queue")
        else:
            self.play_list[ctx.guild.id].remove(ctx.author)
            del self.user_state[ctx.author.id]
            await ctx.send(f"Ok we have {len(self.play_list[ctx.guild.id])} users now")

    @commands.dm_only()
    @commands.command()
    async def l(self, ctx):
        if ctx.author.id in self.user_state and not isinstance(self.user_state[ctx.author.id], str):
            # user is in a game
            await self.user_state[ctx.author.id].player_leave(ctx.author)

    @commands.command()
    async def play(self, ctx, game_name):
        if ctx.guild.id not in self.play_list or len(self.play_list[ctx.guild.id]) < 1:
            await ctx.send("There is no one in the list")
            return

        if game_name in games:
            await ctx.send("Ok")

            players = []

            for player in self.play_list[ctx.guild.id]:
                try:
                    await player.send(f"A {game_name} game is starting from {ctx.guild.name},"
                                      f" use {self.bot.command_prefix}l to leave the game")

                    players.append(player)
                except discord.Forbidden:
                    await ctx.send(f"I couldn't message {player.mention}, this user won't be playing >:(")

            # gets the game constructor
            instance = games[game_name](self, ctx.channel, players)

            # clears the individual user state of all the people that were in the queue
            for player in self.play_list[ctx.guild.id]:
                del self.user_state[player.id]

            # assigns the game instance to the players
            # this step is separated from the one above because the players that will actually play
            # might be different from the original queue
            for player in players:
                self.user_state[player.id] = instance

            # deletes the queue
            del self.play_list[ctx.guild.id]

            # adds the game to the queue

            self.game_instances.append(instance)
            await instance.on_start()
        else:
            await ctx.send("There's no game named that")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content.startswith(f"{self.bot.command_prefix}l"):
            return
        for instance in self.game_instances:
            for player in instance.players:
                player: discord.User

                # check if the message is pertinent for this instance
                if message.channel.id == player.dm_channel.id and \
                        message.author.id == player.id:

                    async with instance.lock:
                        if instance.running:
                            try:
                                await instance.on_message(message)
                            except Exception as e:
                                await instance.end_game(EndGame.ERROR, e)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        for instance in self.game_instances:
            for player in instance.players:
                player: discord.User

                # check if the reaction is pertinent for this instance
                if reaction.message.channel.id == player.dm_channel.id and \
                        user.id == player.id:

                    async with instance.lock:
                        if instance.running:
                            try:
                                await instance.on_reaction_add(reaction, user)
                            except Exception as e:
                                await instance.end_game(EndGame.ERROR, e)


def setup(bot):
    bot.add_cog(GameCog(bot))
