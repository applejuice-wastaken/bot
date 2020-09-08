import discord
from discord.ext import commands

from games.uno import uno


games = {"uno": uno.UnoGame}


class Game(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_state = {}
        self.game_instances = []
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
    async def speak(self, ctx, *, content):
        if ctx.author.id in self.user_state and not isinstance(self.user_state[ctx.author.id], str):
            as_member = self.user_state[ctx.author.id].guild.get_member(ctx.author.id)
            for player in self.user_state[ctx.author.id].players:
                if player.id != ctx.author.id:
                    await player.send(f"**{as_member.display_name}:** {content}")

    @commands.dm_only()
    @commands.command()
    async def leave(self, ctx):
        if ctx.author.id in self.user_state and not isinstance(self.user_state[ctx.author.id], str):
            if await self.user_state[ctx.author.id].player_leave(ctx.author):
                del self.user_state[ctx.author.id]

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
                                      f" use {self.bot.command_prefix}speak in this channel to talk "
                                      f"to the other players and {self.bot.command_prefix}leave to leave the game")

                    players.append(player)
                except discord.Forbidden:
                    await ctx.send(f"I couldn't message {player.mention}, this user won't be playing >:(")

            instance = games[game_name](self.bot, ctx.guild, players)

            for player in self.play_list[ctx.guild.id]:
                del self.user_state[player.id]

            for player in players:
                self.user_state[player.id] = instance
            del self.play_list[ctx.guild.id]

            self.game_instances.append(instance)
            await instance.run()
            self.game_instances.remove(instance)

            for player in self.play_list[ctx.guild.id]:
                del self.user_state[player.id]

def setup(bot):
    bot.add_cog(Game(bot))
