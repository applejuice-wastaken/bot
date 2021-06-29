import functools
import typing

from async_lru import alru_cache

from .abc import FlagRetriever
from .flag import Flag


@functools.lru_cache()
def get_retrievers() -> typing.List[FlagRetriever]:
    from .country_flag import CountryFlagRetriever
    from .lgbt_flag import LGBTFlagRetriever
    from .local_flag import LocalFlagRetriever

    return [LocalFlagRetriever(), CountryFlagRetriever(), LGBTFlagRetriever()]


@alru_cache
async def get_flag(name, schema=None) -> typing.Optional[Flag]:
    for retriever in get_retrievers():
        if schema is None or retriever.schema == schema:
            ret = await retriever.get_flag(name)

            if ret is not None:
                return ret
