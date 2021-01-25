import asyncio
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import Dict, Any, Optional, Iterable, List
import discord

def process_render_changes(o: dict, n: dict) -> Dict[str, Any]:
    ret = {}
    for key in o:
        ret[key] = None

    for key, val in n.items():
        other_value = o.get(key, None)

        if isinstance(val, discord.Embed) and isinstance(other_value, discord.Embed):
            is_equal = other_value.to_dict() == val.to_dict()
        elif not isinstance(val, discord.Embed) and not isinstance(other_value, discord.Embed):
            is_equal = val == other_value
        else:
            is_equal = False

        if is_equal:
            del ret[key]
        else:
            ret[key] = val
    return ret

async def sync_reactions(message: discord.Message, reactions: Iterable[str]):
    message = await message.channel.fetch_message(message.id)  # get updated message
    message: discord.Message

    message_reactions = message.reactions
    message_reaction_idx = 0

    for new_reaction in reactions:
        if message_reaction_idx < len(message_reactions):
            while new_reaction != message_reactions[message_reaction_idx].emoji and \
                    message_reaction_idx < len(message_reactions):
                await message.clear_reaction(message_reactions[message_reaction_idx])
                message_reaction_idx += 1

        await message.add_reaction(new_reaction)
        message_reaction_idx += 1

    while message_reaction_idx < len(message_reactions):
        await message.clear_reaction(message_reactions[message_reaction_idx])
        message_reaction_idx += 1


async def send_reactions(message: discord.Message, reactions: Iterable[str]):
    for reaction in reactions:
        await message.add_reaction(reaction)

def _check_updates(func):
    async def wrapper(self, *args, **kwargs):
        async with self.lock:
            await func(self, *args, **kwargs)
            await self.check_update()

    return wrapper

class ReactiveMessage(ABC):
    ATTEMPT_REUSE_REACTIONS = False

    def __init__(self, cog, channel):
        self.cog = cog
        self.channel: discord.TextChannel = channel
        self.bound_message: Optional[discord.Message] = None
        self.current_render = None
        self.requires_render = False
        self.running = True

        self.lock = asyncio.Lock()

    @abstractmethod
    def render_message(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def update_from_dict(self, d, edit=False):
        if edit:
            changes = process_render_changes(self.current_render, d)

            if len(changes) > 0:  # if something changed
                reactions_changed = "reactions" in changes
                new_reactions = changes.pop("reactions", ())
                if new_reactions is None:
                    new_reactions = ()

                if len(changes) > 0:  # not just the reactions changed
                    await self.bound_message.edit(**changes)

                if reactions_changed:  # if the reactions changed
                    if self.ATTEMPT_REUSE_REACTIONS:
                        await sync_reactions(self.bound_message, new_reactions)
                    else:
                        with suppress(discord.Forbidden):
                            await self.bound_message.clear_reactions()

                        await send_reactions(self.bound_message, new_reactions)

            self.current_render = d
        else:
            to_delete = None

            if self.bound_message is not None:
                to_delete = self.bound_message

            self.current_render = d.copy()
            reactions = d.pop("reactions", None)

            self.bound_message = await self.channel.send(**d)

            if to_delete is not None:
                await to_delete.delete()
                # the old message is called now because of the cog possibly removing this instance from this

            if reactions is not None:
                await send_reactions(self.bound_message, reactions)

    async def update(self, edit=False):
        message_kwargs = await discord.utils.maybe_coroutine(self.render_message)
        await self.update_from_dict(message_kwargs, edit)

    async def check_update(self):
        if self.requires_render:
            await self.update(True)

    async def send_message(self):
        await self.update()

    async def update_message(self):
        await self.update(True)

    async def on_reaction_add(self, reaction, user):
        """this event is limited to the bound message"""
        pass

    async def on_message(self, message):
        """this event is limited to the channel"""
        pass

    @_check_updates
    async def process_message(self, message):
        await self.on_message(message)

    @_check_updates
    async def process_reaction_add(self, reaction, user):
        await self.on_reaction_add(reaction, user)

    async def remove(self):
        if self.running:
            print("removing")
            self.running = False
            bound = self.bound_message
            self.bound_message = None
            with suppress(discord.NotFound):
                await bound.delete()
            self.cog.react_menus.remove(self)
