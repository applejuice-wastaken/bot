import asyncio
from abc import ABC, abstractmethod
from contextlib import suppress
from functools import wraps
from typing import Dict, Any, Optional, Iterable

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
            while message_reaction_idx < len(message_reactions) and \
                    new_reaction != message_reactions[message_reaction_idx].emoji:
                await message.clear_reaction(message_reactions[message_reaction_idx])
                message_reaction_idx += 1

        if message_reaction_idx >= len(message_reactions) or not message_reactions[message_reaction_idx].me:
            await message.add_reaction(new_reaction)

        message_reaction_idx += 1

    while message_reaction_idx < len(message_reactions):
        await message.clear_reaction(message_reactions[message_reaction_idx])
        message_reaction_idx += 1


async def send_reactions(message: discord.Message, reactions: Iterable[str]):
    for reaction in reactions:
        await message.add_reaction(reaction)


def human_join_list(input_list: list, analyse_contents=False):
    if len(input_list) == 0:
        return ""
    elif len(input_list) == 1:
        return input_list[0]
    elif analyse_contents and " and " in input_list[-1]:
        return ", ".join(input_list)
    else:
        return " and ".join((", ".join(input_list[:-1]), input_list[-1]))


def format_permissions(perms):
    return f"this message requires " \
           f"{human_join_list([perm.replace('_', ' ').replace('guild', 'server').title() for perm in perms])}" \
           f" permission(s) in order to be rendered properly\nNormal execution should resume if permissions " \
           f"are satisfied"


def _strip_only_message(data):
    ret = {}

    for attr in "content", "embed":
        if attr in data:
            ret[attr] = data[attr]

    return ret


def checks_updates(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        async with self.lock:
            await func(self, *args, **kwargs)
            await self.check_update()

    return wrapper


class ReactiveMessage(ABC):
    ENFORCE_REACTION_POSITIONS = True

    def __init__(self, bot, channel):
        self.bot = bot

        self.channel: discord.TextChannel = channel

        self.bound_message: Optional[discord.Message] = None

        self.current_displaying_render = None  # what is absolutely rendered to discord
        self.message_render = None
        # what should be rendered; both values can be different if permission checks fail
        # as message render will be pointing to what should be rendered to discord if permissions
        # were granted

        self.requires_render = False

        self.running = True

        self.functional = False  # this should be false if the message cannot be rendered properly

        self.lock = asyncio.Lock()

        self.bot.add_listener_object(self)

    def __await__(self):
        # this looks weird lol
        yield from self.send().__await__()
        return self

    @abstractmethod
    def render_message(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def send(self):
        message_kwargs = await discord.utils.maybe_coroutine(self.render_message)
        await self.send_from_dict(message_kwargs)

    # noinspection PyArgumentList
    async def wait_permissions_fulfill(self, changes: dict, send_first_attempt=False):
        self.functional = False
        while True:
            s = self.check_permissions(self.get_required_permissions(changes))

            method = self._send_from_dict if send_first_attempt else self._update_from_dict

            if len(s) == 0:
                self.functional = True
                await method(changes)
                return
            else:
                await method(dict(content=format_permissions(s)))

                def check_channel(channel):
                    return channel.id == self.channel.id

                def check_guild(guild):
                    return guild.id == self.channel.guild.id

                def check_user(user):
                    return user.id == self.bot.user.id

                pending_tasks = [
                    self.bot.wait_for('guild_channel_update', check=lambda before, after: check_channel(after)),
                    self.bot.wait_for('guild_role_update', check=lambda before, after: check_guild(after.guild)),
                    self.bot.wait_for('member_update', check=lambda before, after: check_user(after))]

                done_tasks, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED,
                                                               timeout=30)

                for task in pending_tasks:
                    task.cancel()

                if len(done_tasks) == 0:
                    await self.delete()
                    return
            send_first_attempt = False

    async def send_from_dict(self, d):
        async with self.lock:
            await self.wait_permissions_fulfill(d, True)

            self.message_render = d

    async def _send_from_dict(self, d: dict):
        to_delete = None

        if self.bound_message is not None:
            to_delete = self.bound_message

        self.current_displaying_render = d.copy()
        reactions = d.pop("reactions", None)

        self.bound_message = await self.channel.send(**_strip_only_message(d))

        if to_delete is not None:
            await to_delete.delete()
            # the old message is called now because of the cog possibly removing this instance from this

        if reactions is not None:
            await send_reactions(self.bound_message, reactions)

    async def check_update(self):
        if self.running and self.requires_render:
            await self.update()

    async def update(self):
        message_kwargs = await discord.utils.maybe_coroutine(self.render_message)
        await self.update_from_dict(message_kwargs)

    async def update_from_dict(self, d):
        await self.wait_permissions_fulfill(d, False)

        self.message_render = d

    def check_permissions(self, perms):
        guild = self.channel.guild
        me = guild.me if guild is not None else self.bot.user
        permissions = self.channel.permissions_for(me)

        return [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

    def get_required_permissions(self, message):
        permissions = dict()

        if len(message) > 0:
            reactions_changed = "reactions" in message

            if reactions_changed:
                permissions["add_reactions"] = True
                if self.ENFORCE_REACTION_POSITIONS:
                    permissions["manage_messages"] = True

            if "embed" in message and message["embed"] is not None:
                permissions["embed_links"] = True

        return permissions

    async def _update_from_dict(self, d: dict):
        changes = process_render_changes(self.current_displaying_render, d)

        guild = self.channel.guild
        me = guild.me if guild is not None else self.bot.user
        permissions = self.channel.permissions_for(me)

        reaction_re_sync_required = False  # true if updating reactions wasn't totally possible

        if len(changes) > 0:  # if something changed
            reactions_changed = "reactions" in changes
            new_reactions = changes.pop("reactions", ())
            if new_reactions is None:
                new_reactions = ()

            if len(changes) > 0:  # not just the reactions changed
                await self.bound_message.edit(**_strip_only_message(changes))

            if reactions_changed:  # if the reactions changed
                reaction_group_changed = "reaction_group" in changes

                try:
                    if not reaction_group_changed:
                        if permissions.manage_messages and permissions.add_reactions:
                            await sync_reactions(self.bound_message, new_reactions)
                        else:
                            reaction_re_sync_required = True
                    else:
                        if permissions.manage_messages:
                            await self.bound_message.clear_reactions()
                        else:
                            reaction_re_sync_required = True

                        if permissions.add_reactions:
                            await send_reactions(self.bound_message, new_reactions)
                        else:
                            reaction_re_sync_required = True

                except discord.Forbidden:
                    reaction_re_sync_required = True

        if reaction_re_sync_required:
            message = await self.channel.fetch_message(self.bound_message.id)

            d["reactions"] = [reaction.emoji for reaction in message.reactions]

        self.current_displaying_render = d

    async def process_reaction_add(self, reaction, user):
        """this event is limited to the bound message"""
        pass

    async def process_message(self, message):
        """this event is limited to the channel"""
        pass

    @checks_updates
    async def on_message(self, message):
        if self.functional and message.channel.id == self.channel.id and self.bot.user.id != message.author.id:
            await self.process_message(message)

    @checks_updates
    async def on_reaction_add(self, reaction, user):
        if self.bound_message is None:
            return

        if self.functional and self.bound_message.id == reaction.message.id and self.bot.user.id != user.id:
            await self.process_reaction_add(reaction, user)

    async def remove(self):
        if self.running:
            self.bot.remove_listener_object(self)

            self.running = False

    async def delete(self):
        if self.running:
            await self.remove()
            bound = self.bound_message
            self.bound_message = None
            if bound is not None:
                with suppress(discord.NotFound):
                    await bound.delete()
