import asyncio
from contextlib import suppress
from typing import Type, Dict, Any, Tuple
import base64
import discord

from games.Game import Game
from games.GameSetting import GameSetting
from reactive_message.HoistedReactiveMessage import HoistedReactiveMessage
from reactive_message.RenderingProperty import RenderingProperty
from reactive_message.RoutedReactiveMessage import RoutedReactiveMessage, Page, Route


def convert(value, data_type: Type):
    if data_type is str:
        return value

    if data_type is int:
        return int(value)

    if data_type is float:
        return float(value)


class MainPage(Page):
    JOIN_LOBBY = "\u2795"
    LEAVE_LOBBY = "\u2796"
    CANCEL_LOBBY = "\u2716\ufe0f"
    PLAY_GAME = "\u25b6\ufe0f"
    SETTINGS_PAGE = "\u2699\ufe0f"

    def render_message(self) -> Dict[str, Any]:
        embed = discord.Embed(title=f"{self.ctx.game_class.game_name} game",
                              color=0x333333)

        if len(self.ctx.queued_players) > 0:
            body = "\n".join(member.mention for member in self.ctx.queued_players)
        else:
            body = "<empty>"

        embed.add_field(name="Players", value=body)

        if len(self.ctx.game_settings_proto) > 0:
            embed.set_footer(text="This game contains settings")
            reactions = (self.JOIN_LOBBY, self.LEAVE_LOBBY, self.CANCEL_LOBBY, self.SETTINGS_PAGE, self.PLAY_GAME)
        else:
            reactions = (self.JOIN_LOBBY, self.LEAVE_LOBBY, self.CANCEL_LOBBY, self.PLAY_GAME)

        return dict(embed=embed, reactions=reactions)

    async def on_reaction_add(self, reaction, user):
        reactive_message: GameLobby
        if reaction.emoji == self.JOIN_LOBBY:
            if user not in self.ctx.queued_players and user.id not in self.ctx.game_cog.user_state:
                self.ctx.game_cog.user_state[user.id] = self
                self.ctx.queued_players.append(user)

        elif reaction.emoji == self.LEAVE_LOBBY:
            if user in self.ctx.queued_players:
                del self.ctx.game_cog.user_state[user.id]
                self.ctx.queued_players.remove(user)

        elif reaction.emoji == self.CANCEL_LOBBY:
            if user.id == self.ctx.owner.id:
                await self.ctx.remove()

        elif reaction.emoji == self.SETTINGS_PAGE:
            if len(self.ctx.game_settings_proto) > 0 and user.id == self.ctx.owner.id:
                self.ctx.route = "settings"

        elif reaction.emoji == self.PLAY_GAME:
            if user.id == self.ctx.owner.id:
                await self.ctx.game_cog.begin_game_for_lobby(self.current_message)

        self.ctx.requires_render = True


async def request(bot, reactive_message, text, value_type, check):
    messages = [await reactive_message.channel.send(text)]

    try:
        message = await bot.wait_for('message', check=check, timeout=30)
        messages.append(message)
        val = message.content
    except asyncio.TimeoutError:
        reactive_message.editing_setting = False
        await reactive_message.check_update()
        await reactive_message.channel.send("timed out", delete_after=10)
        val = None

    if val is not None:
        return convert(val, value_type)


class SettingsPage(Page):
    BACK_TO_MAIN = "\u25c0\ufe0f"
    REWRITE_SETTING = "\u270f\ufe0f"
    SAVE = "\U0001f4be"
    LOAD = "\U0001f4e5"

    def render_message(self) -> Dict[str, Any]:
        embed = discord.Embed(title=f"{self.ctx.game_class.game_name} game",
                              color=0x333333)

        if len(self.ctx.game_settings_proto) > 0:
            body = "\n".join(f"{idx}: {val.display}: "
                             f"{self.ctx.game_settings[key]}"
                             for idx, (key, val) in enumerate(self.ctx.game_settings_proto.items()))
        else:
            body = "<empty (I don't even know how you got here)>"

        embed.add_field(name="Settings", value=body)

        return dict(embed=embed, reactions=(self.BACK_TO_MAIN, self.REWRITE_SETTING, self.SAVE, self.LOAD))

    async def on_reaction_add(self, reaction, user):
        reactive_message: GameLobby
        if reaction.emoji == self.BACK_TO_MAIN:
            if user.id == self.ctx.owner.id:
                self.ctx.route = ""

        elif reaction.emoji == self.SAVE:
            to_save = {}

            for key, val in self.ctx.game_settings_proto.items():
                if self.ctx.game_settings[key] != val.default:
                    to_save[key] = self.ctx.game_settings[key]

            if len(to_save) > 0:
                out = ";".join(f"{key}:{val}" for key, val in to_save.items()).encode()

                result = base64.b85encode(out).decode()

                await self.ctx.channel.send(f"Code: `{result}`")
            else:
                await self.ctx.channel.send("The settings are all set to default values", delete_after=10)

        elif reaction.emoji == self.LOAD:
            bot = self.ctx.game_cog.bot

            def check(m):
                return m.channel == self.ctx.channel and m.author == self.ctx.owner

            code = await request(bot, self.ctx, "Send code", str, check)

            content = base64.b85decode(code.encode()).decode()

            to_load = dict(particle.split(":")[:2] for particle in content.split(";"))

            for key, val in self.ctx.game_settings_proto.items():
                if key in to_load:
                    self.ctx.game_settings[key] = convert(to_load[key], val.setting_type)

        elif reaction.emoji == self.REWRITE_SETTING:
            if user.id == self.ctx.owner.id:
                bot = self.ctx.game_cog.bot

                def check(m):
                    try:
                        _idx = int(m.content)
                    except ValueError:
                        return False
                    else:
                        return m.channel == self.ctx.channel and m.author == self.ctx.owner and \
                               0 <= _idx < len(self.ctx.game_settings_proto)

                idx = await request(bot, self.ctx, "Send the index of the setting you want to access", int, check)

                if idx is not None:
                    picked_setting = [i for i in self.ctx.game_settings_proto.items()][idx]
                    picked_setting: Tuple[str, GameSetting]

                    def check(m):
                        return m.channel == self.ctx.channel and m.author == self.ctx.owner

                    val = await request(bot, self.ctx,
                                        "Send the new value of this setting", picked_setting[1].setting_type, check)

                    if val is not None:
                        self.ctx.game_settings[picked_setting[0]] = val

        self.ctx.requires_render = True


class GameLobby(RoutedReactiveMessage, HoistedReactiveMessage):
    ROUTE = (Route()
             .add_route("settings", SettingsPage())
             .base(MainPage()))

    editing_which = RenderingProperty("editing_which")

    def __init__(self, cog, channel, game_class: Type[Game], owner, game_cog):
        super(GameLobby, self).__init__(cog, channel)
        self.game_cog = game_cog
        self.game_class = game_class
        self.owner = owner
        self.queued_players = []
        self.editing_setting = False
        self.editing_which = None
        self.game_settings_proto = game_class.calculate_game_settings()
        self.game_settings = dict((key, val.default) for key, val in self.game_settings_proto.items())

    async def remove(self):
        for queued in self.queued_players:
            del self.game_cog.user_state[queued.id]

        self.game_cog.lobbies.remove(self)
        await super(GameLobby, self).remove()
