from typing import List, Type, Any, Dict, Tuple, Iterable, Collection

import discord
from discord.ext import commands

from cogs.gamecog.GameLobby import GameLobby
from games.Game import Game, EndGame
from games.GamePlayer import GamePlayer
from games.game_modules.blackjack import blackjack
from games.game_modules.trivia import trivia
from games.game_modules.uno import uno
from util.HoistMenu import HoistMenu

games = {"uno": uno.UnoGame, "trivia": trivia.TriviaGame, "blackjack": blackjack.BlackJackGame}


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

        lobby = GameLobby(ctx.channel, games[game_name], ctx.author, self)
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
        instance_class = lobby.game_class

        for player in lobby.queued_players:
            try:
                await player.send(f"A {instance_class.game_name} game is starting,"
                                  f" use {self.bot.command_prefix}l to leave the game")
            except discord.Forbidden:
                pass
            else:
                players.append(instance_class.game_player_class(player, await player.create_dm()))

        if not instance_class.is_playable(len(players)):
            await lobby.channel.send(f"Game does not support current player count")
            return

        # gets the game constructor
        instance = instance_class(self, lobby.channel, players, lobby.game_settings)

        for player in players:
            player.game_instance = instance

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
                await lobby.on_reaction(reaction, user)
                return
