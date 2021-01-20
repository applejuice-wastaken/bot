import asyncio
from contextlib import suppress
from typing import Type, Tuple, Dict, Any

import discord

from games.Game import Game
from util.HoistMenu import HoistMenu


class GameLobby(HoistMenu):
    def __init__(self, channel, game_class: Type[Game], owner, cog):
        super().__init__(channel)
        self.cog = cog
        self.game_class = game_class
        self.owner = owner
        self.queued_players = []
        self.showing_settings = False
        self.editing_setting = False
        self.game_settings = dict((key, val.default) for key, val in self.game_class.game_settings.items())

    def generate_main_page(self):
        embed = discord.Embed(title=f"{self.game_class.game_name} game",
                              color=0x333333)

        if len(self.queued_players) > 0:
            body = "\n".join(member.mention for member in self.queued_players)
        else:
            body = "<empty>"

        embed.add_field(name="Players", value=body)

        if len(self.game_class.game_settings) > 0:
            embed.set_footer(text="This game contains settings")
            reactions = "➕➖✖⚙▶"
        else:
            reactions = "➕➖✖▶"

        return "", {"embed": embed, "reactions": reactions}

    def generate_settings_page(self):
        embed = discord.Embed(title=f"{self.game_class.game_name} game",
                              color=0x333333)
        embed.set_footer(text="This game contains settings")

        if len(self.game_class.game_settings) > 0:
            body = "\n".join(f"{str(idx) + ': ' if self.editing_setting else ''}"
                             f"{val.display}: {self.game_settings[key]}"
                             for idx, (key, val) in enumerate(self.game_class.game_settings.items()))
        else:
            body = "<empty (I don't even know how you got here)>"

        embed.add_field(name="Settings", value=body)

        return "", {"embed": embed, "reactions": "◀✏"}

    def build_message(self) -> Tuple[str, Dict[str, Any]]:
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
            if reaction.emoji == "◀":
                if user.id == self.owner.id:
                    self.showing_settings = False
                    await self.update_message()

            elif reaction.emoji == "✏":
                if user.id == self.owner.id:
                    self.editing_setting = True
                    await self.update_message()

                    def check(m):
                        try:
                            _idx = int(m.content)
                        except ValueError:
                            return False
                        else:
                            return m.channel == self.channel and m.author == self.owner and \
                                    0 <= _idx < len(self.game_class.game_settings)
                    await reaction.message.channel.send("Send the index of the setting you want to change")

                    try:
                        message = await bot.wait_for('message', check=check, timeout=30)
                    except asyncio.TimeoutError:
                        self.editing_setting = False
                        await self.update_message()
                        await reaction.message.channel.send("timed out")
                        return

                    idx = int(message.content)

                    picked_setting = [i for i in self.game_class.game_settings.items()][idx]

                    self.editing_setting = False
                    await self.update_message()

                    def check(m):
                        return m.channel == self.channel and m.author == self.owner

                    await reaction.message.channel.send("Send the new value of this setting")

                    try:
                        message = await bot.wait_for('message', check=check, timeout=30)
                    except asyncio.TimeoutError:
                        await reaction.message.channel.send("timed out")
                        return

                    if picked_setting[1].setting_type is int:
                        try:
                            value = int(message.content)
                        except ValueError:
                            await reaction.message.channel.send("This isn't a number")
                            return
                    else:
                        raise

                    if picked_setting[1].validator(value):
                        self.game_settings[picked_setting[0]] = value

                        await self.update_message()
                    else:
                        await reaction.message.channel.send("this value cannot be validated")
        else:
            if reaction.emoji == "➕":
                if user not in self.queued_players and user.id not in self.cog.user_state:
                    self.cog.user_state[user.id] = self
                    self.queued_players.append(user)
                    await self.update_message()

            elif reaction.emoji == "➖":
                if user in self.queued_players:
                    del self.cog.user_state[user.id]
                    self.queued_players.remove(user)
                    await self.update_message()

            elif reaction.emoji == "✖":
                if user.id == self.owner.id:
                    for queued in self.queued_players:
                        del self.cog.user_state[queued.id]

                    await self.bound_message.delete()
                    self.cog.lobbies.remove(self)  # this is fine because the loop is broken later

            elif reaction.emoji == "⚙":
                if len(self.game_class.game_settings) > 0 and user.id == self.owner.id:
                    self.showing_settings = True
                    await self.update_message()

            elif reaction.emoji == "▶":
                if user.id == self.owner.id:
                    await self.cog.begin_game_for_lobby(self)
