from __future__ import annotations

import abc
import contextlib
import enum
import typing
from typing import TYPE_CHECKING

import nextcord
from nextcord import Interaction
from nextcord.ext.commands import Context

if TYPE_CHECKING:
    pass


class ResponseKind(enum.Enum):
    NORMAL = enum.auto()
    FAILURE = enum.auto()


class ResponsePrivacyKind(enum.Enum):
    NORMAL = enum.auto()
    PRIVATE_IF_POSSIBLE = enum.auto()
    PRIVATE_AT_ALL_COSTS = enum.auto()


class CommandResponseChunk:
    def __init__(self, owner: CommandInterop):
        self.owner = owner
        self.text = ""

    def __str__(self):
        return self.text

    async def set(self, text=""):
        self.text = text
        await self.owner.update_text_chunks()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.remove()

    # noinspection PyProtectedMember
    def remove(self):
        idx = self.owner._message_chunks.index(self)
        if idx != -1:
            self.owner._message_chunks.pop(idx)

    async def destroy(self):
        self.remove()
        await self.owner.update_text_chunks()


class CommandInterop(abc.ABC):
    def __init__(self):
        self._message_chunks = []

    @classmethod
    def from_command(cls, ctx: Context):
        return TraditionalCommandInterop(ctx)

    @classmethod
    def from_slash_interaction(cls, interaction: Interaction):
        return SlashCommandInterop(interaction)

    @abc.abstractmethod
    async def respond(self, *args, kind: ResponseKind = ResponseKind.NORMAL,
                      privacy: ResponsePrivacyKind = ResponsePrivacyKind.NORMAL,
                      **kwargs):
        pass

    @contextlib.asynccontextmanager
    @abc.abstractmethod
    async def loading(self,
                      kind: ResponseKind = ResponseKind.NORMAL,
                      privacy: ResponsePrivacyKind = ResponsePrivacyKind.NORMAL
                      ):
        pass

    @property
    @abc.abstractmethod
    def channel(self):
        pass

    @property
    @abc.abstractmethod
    def author(self):
        pass

    @property
    @abc.abstractmethod
    def invoker_message(self):
        pass

    @property
    @abc.abstractmethod
    def sent_message(self):
        pass

    async def update_text_chunks(self):
        return await self.respond("\n".join(str(chunk) for chunk in self._message_chunks))

    def chunk(self):
        chunk = CommandResponseChunk(self)
        self._message_chunks.append(chunk)
        return chunk


class TraditionalCommandInterop(CommandInterop):
    @property
    def channel(self):
        return self.ctx.channel

    @property
    def author(self):
        return self.ctx.author

    @property
    def invoker_message(self):
        return self.ctx.message

    @property
    def sent_message(self):
        return self._respond_message

    def __init__(self, ctx):
        super().__init__()

        self.ctx: Context = ctx
        self._respond_message: typing.Optional[nextcord.Message] = None

    async def respond(self, *args, kind: ResponseKind = ResponseKind.NORMAL,
                      privacy: ResponsePrivacyKind = ResponsePrivacyKind.NORMAL,
                      **kwargs):

        if self._respond_message is not None:
            return await self._respond_message.edit(*args, **kwargs)

        if privacy == ResponsePrivacyKind.PRIVATE_AT_ALL_COSTS:
            target = self.ctx.author

        else:
            target = self.ctx

        if kind == ResponseKind.FAILURE:
            m = await target.send(*args, **kwargs, delete_after=10)

            if privacy == ResponsePrivacyKind.PRIVATE_AT_ALL_COSTS:
                await self.ctx.message.delete()

            else:
                await self.ctx.message.delete(delay=10)

            self._respond_message = m
            return m

        else:
            self._respond_message = await target.send(*args, **kwargs)
            return self._respond_message

    @contextlib.asynccontextmanager
    async def loading(self,
                      kind: ResponseKind = ResponseKind.NORMAL,
                      privacy: ResponsePrivacyKind = ResponsePrivacyKind.NORMAL
                      ):

        async with self.ctx.typing():
            yield


class SlashCommandInterop(CommandInterop):
    @property
    def channel(self):
        return self.interaction.channel

    @property
    def author(self):
        return self.interaction.user

    @property
    def invoker_message(self):
        return self.interaction.message

    @property
    def sent_message(self):
        return None

    def __init__(self, interaction: Interaction):
        super().__init__()

        self.interaction = interaction

    async def respond(self, *args,
                      kind: ResponseKind = ResponseKind.NORMAL,
                      privacy: ResponsePrivacyKind = ResponsePrivacyKind.NORMAL,
                      **kwargs):
        if self.interaction.response.is_done():
            if args:
                kwargs["content"] = args[0]
                args = args[1:]

            await self.interaction.edit_original_message(*args, **kwargs)
        else:
            if kind == ResponseKind.FAILURE or privacy != ResponsePrivacyKind.NORMAL:
                await self.interaction.send(*args, **kwargs, ephemeral=True)

            else:
                await self.interaction.send(*args, **kwargs)

    @contextlib.asynccontextmanager
    async def loading(self,
                      kind: ResponseKind = ResponseKind.NORMAL,
                      privacy: ResponsePrivacyKind = ResponsePrivacyKind.NORMAL
                      ):
        if not self.interaction.response.is_done():
            await self.interaction.response.defer()

        yield
