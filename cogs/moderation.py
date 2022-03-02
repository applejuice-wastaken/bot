import dataclasses
import datetime
import typing
from collections import deque

import nextcord
from nextcord.ext import commands
from nextcord import SlashOption, Interaction

from etcetra.human_join_list import human_join_list
from etcetra.interops import CommandInterop, ResponseKind, TraditionalCommandInterop


@dataclasses.dataclass(frozen=True)
class Record:
    message_id: int
    deleted_messages: int = 0
    authors: set = dataclasses.field(default_factory=set)
    pinged_roles: set = dataclasses.field(default_factory=set)
    pinged_users: set = dataclasses.field(default_factory=set)
    pinged_everyone: bool = False
    times: int = 1


class Moderation(commands.Cog):
    DOWN = "\U0001f53d"
    UP = "\U0001f53c"

    def __init__(self, bot):
        self.bot = bot

        self.purge_info: deque[Record] = deque(maxlen=30)

    async def purge_action(self, resp: CommandInterop, messages: typing.List[nextcord.Message]):
        messages.sort(key=lambda value: value.id, reverse=True)

        for message in messages:
            age = datetime.datetime.now() - message.created_at.replace(tzinfo=None)
            if age.days > 14:
                await resp.respond("No can do; there's messages older than 14 days", failure=True)
                break

        else:
            deleted = 0
            pinged_roles = set()
            pinged_users = set()
            authors = {resp.author}
            pinged_everyone = False
            times = 1

            for message in messages:
                info = nextcord.utils.find(lambda other: other.message_id == message.id, self.purge_info)
                if info is not None:
                    info: Record

                    deleted += info.deleted_messages

                    authors |= info.authors
                    pinged_roles |= info.pinged_roles
                    pinged_users |= info.pinged_users
                    pinged_everyone |= info.pinged_everyone
                    times += info.times

                for role in message.role_mentions:
                    pinged_roles.add(role)

                for user in message.mentions:
                    pinged_users.add(user)

                pinged_everyone |= message.mention_everyone
                deleted += 1

            while len(messages) > 0:
                await resp.channel.delete_messages(messages[:100])
                messages = messages[100:]

            main_chunk = f"Deleted {deleted} Messages"

            if isinstance(resp, TraditionalCommandInterop):
                main_chunk += f" issued by {human_join_list([author.mention for author in authors])}"

            appended_info = []

            if pinged_users:
                appended_info.append(f"{len(pinged_users)} user{'' if len(pinged_users) == 1 else 's'}")

            if pinged_roles:
                appended_info.append(f"{len(pinged_roles)} role{'' if len(pinged_roles) == 1 else 's'}")

            if pinged_everyone:
                appended_info.append("everyone")

            if appended_info:
                main_chunk += ", that pinged "

            trace = await resp.respond(f"*[{main_chunk + human_join_list(appended_info)}]*")

            if trace is not None:
                self.purge_info.append(Record(trace.id, deleted, authors,
                                              pinged_roles, pinged_users, pinged_everyone, times))

    async def impl_purge_quantity(self, resp: CommandInterop, quantity: int):
        if quantity <= 1:
            await resp.respond("Has to be higher than 1", kind=ResponseKind.FAILURE)

        else:
            messages = await resp.channel.history(limit=quantity).flatten()
            await self.purge_action(resp, messages)

    async def impl_purge_until(self, resp: CommandInterop, target):
        messages = await resp.channel.history(limit=1000, after=target).flatten()

        if len(messages) <= 1:
            await resp.respond("Insufficient amount of messages")
        else:
            await self.purge_action(resp, messages)

    # groups

    @nextcord.slash_command(name="purge")
    async def s_purge_root(self, interaction):
        pass

    # purge quantity command

    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.group(name="purge", invoke_without_command=True)
    async def c_purge_quantity(self, ctx, quantity: int):
        """Purge an arbitrary amount of messages"""
        await self.impl_purge_quantity(CommandInterop.from_command(ctx), quantity + 1)

    @s_purge_root.subcommand(name="quantity", description="Purge an arbitrary amount of messages")
    async def s_purge_quantity(self, interaction: Interaction, quantity: int = SlashOption(required=True)):
        if not interaction.channel.permissions_for(interaction.user).manage_messages:
            await interaction.send("You can't use this command", ephemeral=True)
            return

        await self.impl_purge_quantity(CommandInterop.from_slash_interaction(interaction), quantity)

    # purge until command

    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @c_purge_quantity.command(name="until")
    async def c_purge_until(self, ctx, message_id: int):
        """Purges until a specified message"""
        await self.impl_purge_until(CommandInterop.from_command(ctx), nextcord.Object(message_id))

    @s_purge_root.subcommand(name="until", description="Purges until a specified message")
    async def s_purge_until(self, interaction: Interaction, message: nextcord.Message):
        if not interaction.channel.permissions_for(interaction.user).manage_messages:
            await interaction.send("You can't use this command", ephemeral=True)
            return

        await self.impl_purge_until(CommandInterop.from_slash_interaction(interaction), message)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        info = nextcord.utils.find(lambda other: other.message_id == message.id, self.purge_info)

        if info:
            self.purge_info.remove(info)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        for message in messages:
            info = nextcord.utils.find(lambda other: other.message_id == message.id, self.purge_info)

            if info:
                self.purge_info.remove(info)


def setup(bot):
    bot.add_cog(Moderation(bot))
