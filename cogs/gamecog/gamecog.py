from typing import List

import discord
from discord import RawReactionActionEvent, Reaction
from discord.ext import commands

from cogs.gamecog.GameLobby import GameLobby
from games.Game import Game
from games.GamePlayer import GamePlayer
from games.game_modules.blackjack import blackjack
from games.game_modules.trivia import trivia
from games.game_modules.uno import uno

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
    async def new(self, ctx, game_name=None):
        """creates a lobby"""
        if game_name is None:
            embed = discord.Embed(title="Games", description="\n".join(games.keys()))
            await ctx.send(embed=embed)
            return

        if game_name not in games:
            await ctx.send("This game does not exist")
            return

        self.lobbies.append(await GameLobby(self.bot, ctx.channel, games[game_name], ctx.author, self))

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

        # deletes the lobby
        lobby.route = "started"

        await lobby.check_update()

        await lobby.remove()

        for player in players:
            self.user_state[player.id] = instance

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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, ev: RawReactionActionEvent):
        if ev.user_id == self.bot.user.id:
            return

        for instance in self.game_instances:
            for player in instance.players:
                player: GamePlayer

                # check if the reaction is pertinent for this instance
                if ev.channel_id == player.bound_channel.id and ev.user_id == player.id:
                    data = dict(message_id=ev.user_id, channel_id=ev.channel_id,
                                user_id=ev.user_id, guild_id=ev.guild_id)

                    message = discord.utils.find(lambda m: m.id == ev.message_id, reversed(self.bot.cached_messages))

                    emoji_id = ev.emoji.id
                    if not emoji_id:
                        emoji = ev.emoji.name
                    else:
                        try:
                            emoji = self.bot.get_emoji(emoji_id)
                        except KeyError:
                            emoji = ev.emoji

                    await instance.call_wrap(instance.on_reaction_add(Reaction(message=message,
                                                                               data=data,
                                                                               emoji=emoji), player))
                    return
