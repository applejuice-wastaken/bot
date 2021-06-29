import abc
import asyncio
from typing import TypeVar, Iterable

T = TypeVar('T')


class AbstractMulticastIntent(abc.ABC):
    def to(self, targets: Iterable[T]):
        return ArbitraryMulticastIntent(targets)

    def excluding(self, *targets: T):
        return ArbitraryMulticastIntent(t for t in self.get_targets() if t not in targets)

    def including(self, *targets: T):
        return ArbitraryMulticastIntent(t for t in (*self.get_targets(), *targets))

    def __getattr__(self, item):
        targets = list(self.get_targets())

        for t in targets:
            getattr(t, item)

        def _(*args, **kwargs):
            coroutines = []
            for target in targets:
                ret = getattr(target, item)(*args, **kwargs)
                if asyncio.iscoroutine(ret):
                    coroutines.append(ret)

            async def _():
                for r in coroutines:
                    await r

            return _()

        return _

    @abc.abstractmethod
    def get_targets(self):
        pass


class ArbitraryMulticastIntent(AbstractMulticastIntent):
    def __init__(self, targets):
        self.targets = targets

    def get_targets(self):
        return self.targets
