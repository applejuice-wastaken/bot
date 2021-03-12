import abc
import typing


class FlagRetriever(abc.ABC):
    @abc.abstractmethod
    def __str__(self):
        pass

    @property
    @abc.abstractmethod
    def schema(self):
        pass

    @abc.abstractmethod
    async def url_from_name(self, name) -> typing.Optional[typing.Tuple[str, str]]:
        pass
