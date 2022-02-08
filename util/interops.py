from __future__ import annotations

import enum
import typing
from typing import TYPE_CHECKING

import nextcord
from nextcord import Interaction
from nextcord.ext.commands import Context

if TYPE_CHECKING:
    pass


class CommandType(enum.Enum):
    COMMAND = enum.auto()
    SLASH_INTERACTION = enum.auto()


class ResponseKind(enum.Enum):
    NORMAL = enum.auto()
    FAILURE = enum.auto()

class ResponsePrivacyKind(enum.Enum):
    NORMAL = enum.auto()
    PRIVATE_IF_POSSIBLE = enum.auto()
    PRIVATE_AT_ALL_COSTS = enum.auto()


class CommandInterop:
    def __init__(self, *, sender, channel, message, author, kind: CommandType):
        self.author: nextcord.Member = author
        self.message: nextcord.Message = message
        self.channel: nextcord.TextChannel = channel
        self.respond: typing.Callable[..., typing.Optional[nextcord.Message]] = sender

        self.kind = kind

    @classmethod
    def from_command(cls, ctx: Context):
        async def sender(*args,
                         kind: ResponseKind = ResponseKind.NORMAL,
                         privacy: ResponsePrivacyKind = ResponsePrivacyKind.NORMAL,
                         **kwargs):

            if privacy == ResponsePrivacyKind.PRIVATE_AT_ALL_COSTS:
                target = ctx.author

            else:
                target = ctx

            if kind == ResponseKind.FAILURE:
                m = await target.send(*args, **kwargs, delete_after=10)

                if privacy == ResponsePrivacyKind.PRIVATE_AT_ALL_COSTS:
                    await ctx.message.delete()

                else:
                    await ctx.message.delete(delay=10)

                return m

            else:
                return await target.send(*args, **kwargs)

        return cls(
            author=ctx.author,
            message=ctx.message,
            channel=ctx.channel,
            sender=sender,

            kind=CommandType.COMMAND
        )

    @classmethod
    async def from_slash_interaction(cls, interaction: Interaction):
        async def sender(*args,
                         kind: ResponseKind = ResponseKind.NORMAL,
                         privacy: ResponsePrivacyKind = ResponsePrivacyKind.NORMAL,
                         **kwargs):
            if kind == ResponseKind.FAILURE or privacy != ResponsePrivacyKind.NORMAL:
                await interaction.send(*args, **kwargs, ephemeral=True)

            else:
                await interaction.send(*args, **kwargs)

        return cls(
            author=interaction.user,
            message=None,
            channel=interaction.channel,
            sender=sender,

            kind=CommandType.SLASH_INTERACTION
        )
