import asyncio
import base64
from contextlib import suppress
from typing import Type, Dict, Any, Tuple

import nextcord

from games.Game import Game
from games.GameSetting import GameSetting
from reactive_message.HoistedReactiveMessage import HoistedReactiveMessage
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
        embed = nextcord.Embed(title=f"{self.message.game_class.game_name} game",
                               color=0x333333)

        if len(self.message.queued_players) > 0:
            body = "\n".join(member.mention for member in self.message.queued_players)
        else:
            body = "<empty>"

        embed.add_field(name="Players", value=body)

        reactions = [self.JOIN_LOBBY, self.LEAVE_LOBBY, self.CANCEL_LOBBY]

        if len(self.message.game_settings_proto) > 0:
            embed.set_footer(text="This game contains settings")
            reactions.append(self.SETTINGS_PAGE)

        if self.message.game_class.is_playable(len(self.message.queued_players)):
            reactions.append(self.PLAY_GAME)

        return dict(embed=embed, reactions=reactions,
                    reaction_group="mp")

    async def process_reaction_add(self, reaction, user):
        reactive_message: GameLobby
        if reaction.emoji == self.JOIN_LOBBY:
            if user not in self.message.queued_players and user.id not in self.message.game_cog.user_state:
                self.message.game_cog.user_state[user.id] = self
                self.message.queued_players.append(user)

        elif reaction.emoji == self.LEAVE_LOBBY:
            if user in self.message.queued_players:
                del self.message.game_cog.user_state[user.id]
                self.message.queued_players.remove(user)

        elif reaction.emoji == self.CANCEL_LOBBY:
            if user.id == self.message.owner.id:
                await self.message.delete()

        elif reaction.emoji == self.SETTINGS_PAGE:
            if len(self.message.game_settings_proto) > 0 and user.id == self.message.owner.id:
                self.message.route = "settings"

        elif reaction.emoji == self.PLAY_GAME:
            if user.id == self.message.owner.id:
                self.message.route = "prepare"

        else:
            return False
        return True


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


def _test(e):
    print(" ".join(hex(ord(letter)) for letter in e))


class PreparePage(Page):
    BACK_TO_MAIN = "\u25c0\ufe0f"
    CONFIRM = "\u2705"
    UNCONFIRMED = "\u274c"
    RESEND = "\U0001f501"

    def __init__(self, message, args: Dict[str, str]):
        message: GameLobby
        super().__init__(message, args)

        self.waiting_confirm = []
        self.confirmed_messages = []
        self.waiting_resend = []

    async def on_enter(self, from_page):
        for player in self.message.queued_players:
            await self.send_confirmation(player)

    async def send_confirmation(self, player):
        try:
            message = await player.send("Waiting confirmation")

            self.waiting_confirm.append((message, player))
        except nextcord.Forbidden:
            self.waiting_resend.append(player)
        else:
            await message.add_reaction(self.CONFIRM)

    async def on_leave(self, to_page):
        if to_page is MainPage:
            for message, _ in self.waiting_confirm:
                await message.edit(content="Start was cancelled")
                await message.delete(delay=30)

            for message in self.confirmed_messages:
                await message.edit(content="Start was cancelled")
                await message.delete(delay=30)

    def render_message(self) -> Dict[str, Any]:
        embed = nextcord.Embed(title=f"{self.message.game_class.game_name} game",
                               color=0x333333)

        players_waiting = [i[1] for i in self.waiting_confirm]

        lines = []
        for player in self.message.queued_players:
            if player in players_waiting:
                emoji = self.UNCONFIRMED
            elif player in self.waiting_resend:
                emoji = self.RESEND
            else:
                emoji = self.CONFIRM

            lines.append(f"{emoji} {player.mention}")

        body = "\n".join(lines)

        embed.add_field(name="Waiting for confirmation", value=body)

        if len(self.waiting_resend) > 0:
            embed.set_footer(text="Enable your DMs (and keep them open) and then react this message")
            reactions = (self.BACK_TO_MAIN, self.RESEND)
        else:
            reactions = (self.BACK_TO_MAIN,)

        return dict(embed=embed, reactions=reactions, reaction_group="pp")

    async def process_reaction_add(self, reaction, user):
        reactive_message: GameLobby
        if reaction.emoji == self.BACK_TO_MAIN:
            if user.id == self.message.owner.id:
                self.message.route = ""

        elif reaction.emoji == self.RESEND:
            if user in self.waiting_resend:
                self.waiting_resend.remove(user)
                await self.send_confirmation(user)
                self.message.requires_render = True

        else:
            return False
        return True

    async def on_raw_reaction_add(self, ev):
        for idx, (message, player) in enumerate(self.waiting_confirm):
            if ev.message_id == message.id and ev.emoji.name == self.CONFIRM and ev.user_id == player.id:
                self.waiting_confirm.pop(idx)
                self.confirmed_messages.append(message)
                if len(self.waiting_confirm) == 0 and len(self.waiting_resend) == 0:
                    await self.message.game_cog.begin_game_for_lobby(self.message)
                    return False
                return True


class SettingsPage(Page):
    BACK_TO_MAIN = "\u25c0\ufe0f"
    REWRITE_SETTING = "\u270f\ufe0f"
    SAVE = "\U0001f4be"
    LOAD = "\U0001f4e5"

    def render_message(self) -> Dict[str, Any]:
        embed = nextcord.Embed(title=f"{self.message.game_class.game_name} game",
                               color=0x333333)

        if len(self.message.game_settings_proto) > 0:
            body = "\n".join(f"{idx}: {val.display}: "
                             f"{self.message.game_settings[key]}"
                             for idx, (key, val) in enumerate(self.message.game_settings_proto.items()))
        else:
            body = "<empty (I don't even know how you got here)>"

        embed.add_field(name="Settings", value=body)

        return dict(embed=embed, reactions=(self.BACK_TO_MAIN, self.REWRITE_SETTING, self.SAVE, self.LOAD),
                    reaction_group="sp")

    async def process_reaction_add(self, reaction, user):
        reactive_message: GameLobby
        if reaction.emoji == self.BACK_TO_MAIN:
            if user.id == self.message.owner.id:
                self.message.route = ""

        elif reaction.emoji == self.SAVE:
            to_save = {}

            for key, val in self.message.game_settings_proto.items():
                if self.message.game_settings[key] != val.default:
                    to_save[key] = self.message.game_settings[key]

            if len(to_save) > 0:
                out = ";".join(f"{key}:{val}" for key, val in to_save.items()).encode()

                result = base64.b85encode(out).decode()

                await self.message.channel.send(f"Code: `{result}`")
            else:
                await self.message.channel.send("The settings are all set to default values", delete_after=10)

        elif reaction.emoji == self.LOAD:
            bot = self.message.game_cog.bot

            def check(m):
                return m.channel == self.message.channel and m.author == self.message.owner

            code = await request(bot, self.message, "Send code", str, check)

            content = base64.b85decode(code.encode()).decode()

            to_load = dict(particle.split(":")[:2] for particle in content.split(";"))

            for key, val in self.message.game_settings_proto.items():
                if key in to_load:
                    self.message.game_settings[key] = convert(to_load[key], val.setting_type)

        elif reaction.emoji == self.REWRITE_SETTING:
            if user.id == self.message.owner.id:
                bot = self.message.game_cog.bot

                def check(m):
                    try:
                        _idx = int(m.content)
                    except ValueError:
                        return False
                    else:
                        return m.channel == self.message.channel and m.author == self.message.owner and \
                               0 <= _idx < len(self.message.game_settings_proto)

                idx = await request(bot, self.message, "Send the index of the setting you want to access", int, check)

                if idx is not None:
                    picked_setting = [i for i in self.message.game_settings_proto.items()][idx]
                    picked_setting: Tuple[str, GameSetting]

                    def check(m):
                        return m.channel == self.message.channel and m.author == self.message.owner

                    val = await request(bot, self.message,
                                        "Send the new value of this setting", picked_setting[1].setting_type, check)

                    if val is not None:
                        self.message.game_settings[picked_setting[0]] = val

        else:
            return False
        return True


class StartedPage(Page):
    def render_message(self) -> Dict[str, Any]:
        embed = nextcord.Embed(title="Game has begun", color=0x333333)

        return dict(embed=embed, reaction_group="stp")


class GameLobby(RoutedReactiveMessage, HoistedReactiveMessage):
    ENFORCE_REACTION_POSITIONS = False

    ROUTE = (Route()
             .add_route("settings", SettingsPage)
             .add_route("prepare", PreparePage)
             .add_route("started", StartedPage)
             .base(MainPage))

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
            with suppress(KeyError):
                del self.game_cog.user_state[queued.id]

        self.game_cog.lobbies.remove(self)
        await super(GameLobby, self).remove()
