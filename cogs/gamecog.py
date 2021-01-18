from typing import List

import discord
from discord.ext import commands

from games.Game import Game, EndGame
from games.GamePlayer import GamePlayer
from games.game_modules.trivia import trivia
from games.game_modules.uno import uno

games = {"uno": uno.UnoGame, "trivia": trivia.TriviaGame}


class GameLobby:
    def __init__(self, game_name, owner, channel):
        self.channel = channel
        self.game_name = game_name
        self.owner = owner
        self.queued_players = []
        self.bound_message = None

        self.messages_before_resending = None

    def generate_embed(self):
        embed = discord.Embed(title=f"{self.game_name} game",
                              color=0x333333)

        if len(self.queued_players) > 0:
            body = "\n".join(member.mention for member in self.queued_players)
        else:
            body = "<empty>"

        embed.add_field(name="Players", value=body)

        return embed

    async def send_message(self):
        self.messages_before_resending = 10

        if self.bound_message is not None:
            await self.bound_message.delete()
        self.bound_message = await self.channel.send(embed=self.generate_embed())

        await self.bound_message.add_reaction("➕")
        await self.bound_message.add_reaction("➖")
        await self.bound_message.add_reaction("✖")
        await self.bound_message.add_reaction("▶")

    async def update_message(self):
        await self.bound_message.edit(embed=self.generate_embed())


class GameCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_state = {}
        self.game_instances: List[Game] = []
        self.lobbies: List[GameLobby] = []

    @commands.group()
    async def game(self, ctx):
        pass

    @commands.guild_only()
    @game.command()
    async def new(self, ctx, game_name):
        """Joins the queue for a game"""

        if game_name not in games:
            await ctx.send("This game does not exist")
            return

        lobby = GameLobby(game_name, ctx.author, ctx.channel)
        self.lobbies.append(lobby)
        await lobby.send_message()

    @commands.dm_only()
    @commands.command()
    async def l(self, ctx):
        if ctx.author.id in self.user_state and not isinstance(self.user_state[ctx.author.id], str):
            # user is in a game

            instance: Game = self.user_state[ctx.author.id]

            await instance.call_wrap(instance.player_leave(instance.player_from_id(ctx.author.id)))

    async def begin_game_for_lobby(self, lobby: GameLobby):
        if len(lobby.queued_players) == 0:
            return

        players = []
        instance_class = games[lobby.game_name]

        for player in lobby.queued_players:
            try:
                await player.send(f"A {lobby.game_name} game is starting,"
                                  f" use {self.bot.command_prefix}l to leave the game")
            except discord.Forbidden:
                pass
            else:
                players.append(instance_class.game_player_class(player, await player.create_dm()))

        if not instance_class.is_playable(len(players)):
            await lobby.channel.send(f"Game does not support current player count")
            return

        # gets the game constructor
        instance = instance_class(self, lobby.channel, players)

        # clears the individual user state of all the people that were in the queue
        for player in lobby.queued_players:
            del self.user_state[player.id]

        # assigns the game instance to the players
        # this step is separated from the one above because the players that will actually play
        # might be different from the original queue
        for player in players:
            self.user_state[player.id] = instance

        # deletes the lobby
        await lobby.bound_message.edit(embed=discord.Embed(title="ok"))
        self.lobbies.remove(lobby)

        # adds the game to the queue

        self.game_instances.append(instance)

        await instance.call_wrap(instance.on_start())

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content.startswith(f"{self.bot.command_prefix}l"):
            return
        for instance in self.game_instances:
            for player in instance.players:
                player: GamePlayer

                # check if the message is pertinent for this instance
                if message.channel.id == player.bound_channel.id and \
                        message.author.id == player.id:

                    await instance.call_wrap(instance.on_message(message, player))
                    return

        for lobby in self.lobbies:
            if lobby.channel.id == message.channel.id:
                lobby.messages_before_resending -= 1
                if lobby.messages_before_resending <= 0:
                    await lobby.send_message()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.id == self.bot.user.id:
            return

        for instance in self.game_instances:
            for player in instance.players:
                player: GamePlayer

                # check if the reaction is pertinent for this instance
                if reaction.message.channel.id == player.bound_channel.id and \
                        user.id == player.id:

                    await instance.call_wrap(instance.on_reaction_add(reaction, player))
                    return

        for lobby in self.lobbies:
            if reaction.message.id == lobby.bound_message.id:
                if reaction.emoji == "➕":
                    if user not in lobby.queued_players and user.id not in self.user_state:
                        self.user_state[user.id] = lobby
                        lobby.queued_players.append(user)
                        await lobby.update_message()

                elif reaction.emoji == "➖":
                    if user in lobby.queued_players:
                        del self.user_state[user.id]
                        lobby.queued_players.remove(user)
                        await lobby.update_message()

                elif reaction.emoji == "✖":
                    if user.id == lobby.owner.id:
                        for queued in lobby.queued_players:
                            del self.user_state[queued.id]

                        await lobby.bound_message.delete()
                        self.lobbies.remove(lobby)  # this is fine because the loop is broken later

                elif reaction.emoji == "▶":
                    if user.id == lobby.owner.id:
                        await self.begin_game_for_lobby(lobby)

                return
def setup(bot):
    bot.add_cog(GameCog(bot))
