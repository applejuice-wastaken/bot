from abc import ABC, abstractmethod


class AttributeFiller(ABC):
    @classmethod
    @abstractmethod
    async def begin(cls, game):
        pass

    @classmethod
    @abstractmethod
    async def on_message(cls, game, message):
        pass

    @classmethod
    @abstractmethod
    async def on_reaction_add(cls, game, reaction, user):
        pass
