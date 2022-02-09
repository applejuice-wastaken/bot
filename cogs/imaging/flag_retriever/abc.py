import abc
import typing

from cogs.imaging.flag_retriever.flag import Flag


class FlagRetriever(abc.ABC):
    @abc.abstractmethod
    def __str__(self):
        pass

    @property
    @abc.abstractmethod
    def schema(self):
        pass

    @abc.abstractmethod
    async def get_flag(self, name) -> typing.Optional[Flag]:
        pass

    async def search(self, name) -> typing.Set[str]:
        return set()
