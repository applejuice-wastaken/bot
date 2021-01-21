import asyncio
from contextlib import suppress
from typing import Type, Tuple, Dict, Any

import discord

from games.Game import Game
from util.HoistMenu import HoistMenu

def convert(value, data_type: Type):
    if data_type is int:
        return int(value)

    if data_type is float:
        return float(value)

class GameLobby(HoistMenu):
    JOIN_LOBBY = "\u2795"
    LEAVE_LOBBY = "\u2796"
    CANCEL_LOBBY = "\u2716\ufe0f"
    PLAY_GAME = "\u25b6\ufe0f"
    SETTINGS_PAGE = "\u2699\ufe0f"
    BACK_TO_MAIN = "\u25c0\ufe0f"
    REWRITE_SETTING = "\u270f\ufe0f"

    def __init__(self, channel, game_class: Type[Game], owner, cog):
        super().__init__(channel)
        self.cog = cog
        self.game_class = game_class
        self.owner = owner
        self.queued_players = []
        self.showing_settings = False
        self.editing_setting = False
        self.editing_which = None
        self.game_settings_proto = game_class.calculate_game_settings()
        self.game_settings = dict((key, val.default) for key, val in self.game_settings_proto.items())

    def generate_main_page(self):
        embed = discord.Embed(title=f"{self.game_class.game_name} game",
                              color=0x333333)

        if len(self.queued_players) > 0:
            body = "\n".join(member.mention for member in self.queued_players)
        else:
            body = "<empty>"

        embed.add_field(name="Players", value=body)

        if len(self.game_settings_proto) > 0:
            embed.set_footer(text="This game contains settings")
            reactions = (self.JOIN_LOBBY, self.LEAVE_LOBBY, self.CANCEL_LOBBY, self.SETTINGS_PAGE, self.PLAY_GAME)
        else:
            reactions = (self.JOIN_LOBBY, self.LEAVE_LOBBY, self.CANCEL_LOBBY, self.PLAY_GAME)

        return {"embed": embed, "reactions": reactions}

    def generate_settings_page(self):
        embed = discord.Embed(title=f"{self.game_class.game_name} game",
                              color=0x333333)
        embed.set_footer(text="This game contains settings")

        if len(self.game_settings_proto) > 0:
            body = "\n".join(f"{str(idx) + ': ' if self.editing_setting else ''}"
                             f"{'__' if self.editing_which == idx else ''}{val.display}: {self.game_settings[key]}"
                             f"{'__' if self.editing_which == idx else ''}"
                             for idx, (key, val) in enumerate(self.game_settings_proto.items()))
        else:
            body = "<empty (I don't even know how you got here)>"

        embed.add_field(name="Settings", value=body)

        return {"embed": embed, "reactions": (self.BACK_TO_MAIN, self.REWRITE_SETTING)}

    def build_message(self) -> Dict[str, Any]:
        if self.showing_settings:
            return self.generate_settings_page()
        else:
            return self.generate_main_page()
    
    async def on_reaction(self, reaction: discord.Reaction, user):
        with suppress(discord.Forbidden):
            await reaction.message.remove_reaction(reaction, user)

        if self.editing_setting:
            return

        bot = self.cog.bot

        if self.showing_settings:
            if reaction.emoji == self.BACK_TO_MAIN:
                if user.id == self.owner.id:
                    self.showing_settings = False
                    await self.update_message()

            elif reaction.emoji == self.REWRITE_SETTING:
                if user.id == self.owner.id:
                    self.editing_setting = True
                    delete_messages = []
                    await self.update_message()

                    def check(m):
                        try:
                            _idx = int(m.content)
                        except ValueError:
                            return False
                        else:
                            return m.channel == self.channel and m.author == self.owner and \
                                    0 <= _idx < len(self.game_settings_proto)

                    delete_messages.append(await self.channel.send("Send the index of the setting you want to change"))

                    try:
                        message = await bot.wait_for('message', check=check, timeout=30)
                    except asyncio.TimeoutError:
                        self.editing_setting = False
                        await self.update_message()
                        await reaction.message.channel.send("timed out", delete_after=10)
                        with suppress(discord.Forbidden):
                            await self.channel.delete_messages(delete_messages)
                        return

                    delete_messages.append(message)

                    idx = int(message.content)

                    picked_setting = [i for i in self.game_settings_proto.items()][idx]

                    self.editing_setting = False
                    self.editing_which = idx
                    await self.update_message()

                    def check(m):
                        return m.channel == self.channel and m.author == self.owner

                    delete_messages.append(await self.channel.send("Send the new value of this setting"))

                    try:
                        message = await bot.wait_for('message', check=check, timeout=30)
                    except asyncio.TimeoutError:
                        await self.channel.send("timed out", delete_after=10)
                        self.editing_which = None
                        await self.update_message()
                        with suppress(discord.Forbidden):
                            await self.channel.delete_messages(delete_messages)
                        return

                    self.editing_which = None

                    delete_messages.append(message)

                    try:
                        value = convert(message.content, picked_setting[1].setting_type)
                    except ValueError:
                        await reaction.message.channel.send("This isn't a valid input", delete_after=10)
                        with suppress(discord.Forbidden):
                            await self.channel.delete_messages(delete_messages)
                        return

                    if picked_setting[1].validator(value):
                        self.game_settings[picked_setting[0]] = value
                    else:
                        await reaction.message.channel.send("this value cannot be validated", delete_after=10)
                    await self.update_message()
                    with suppress(discord.Forbidden):
                        await self.channel.delete_messages(delete_messages)
        else:
            if reaction.emoji == self.JOIN_LOBBY:
                if user not in self.queued_players and user.id not in self.cog.user_state:
                    self.cog.user_state[user.id] = self
                    self.queued_players.append(user)
                    await self.update_message()

            elif reaction.emoji == self.LEAVE_LOBBY:
                if user in self.queued_players:
                    del self.cog.user_state[user.id]
                    self.queued_players.remove(user)
                    await self.update_message()

            elif reaction.emoji == self.CANCEL_LOBBY:
                if user.id == self.owner.id:
                    for queued in self.queued_players:
                        del self.cog.user_state[queued.id]

                    await self.bound_message.delete()
                    self.cog.lobbies.remove(self)  # this is fine because the loop is broken later

            elif reaction.emoji == self.SETTINGS_PAGE:
                if len(self.game_settings_proto) > 0 and user.id == self.owner.id:
                    self.showing_settings = True
                    await self.update_message()

            elif reaction.emoji == self.PLAY_GAME:
                if user.id == self.owner.id:
                    await self.cog.begin_game_for_lobby(self)
