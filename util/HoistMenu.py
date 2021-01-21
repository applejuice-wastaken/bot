from abc import ABC, abstractmethod
from contextlib import suppress
from typing import Tuple, Collection, Dict, Any, Optional, Iterable, List
import collections
import discord


async def send_reactions(messsage: discord.Message, reactions: Iterable[str]):
    for reaction in reactions:
        await messsage.add_reaction(reaction)


class HoistMenu(ABC):
    def __init__(self, channel):
        self.channel: discord.TextChannel = channel
        self.bound_message: Optional[discord.Message] = None
        self.messages_before_resending: Optional[int] = None
        self._past_reactions: Optional[List[str]] = None

    @abstractmethod
    def build_message(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def update(self, edit=False):
        message_kwargs = self.build_message()
        reactions = list(message_kwargs.pop("reactions", ()))

        if edit:
            await self.bound_message.edit(**message_kwargs)

            if self._past_reactions != reactions:
                with suppress(discord.Forbidden):
                    await self.bound_message.clear_reactions()

                self._past_reactions = reactions
                await send_reactions(self.bound_message, reactions)
        else:
            self.bound_message = await self.channel.send(**message_kwargs)
            self._past_reactions = reactions
            await send_reactions(self.bound_message, reactions)

    async def send_message(self):
        self.messages_before_resending = 10

        if self.bound_message is not None:
            await self.bound_message.delete()

        await self.update()

    async def update_message(self):
        await self.update(True)

    async def on_reaction(self, reaction, user):
        pass
