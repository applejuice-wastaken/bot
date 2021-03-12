from async_lru import alru_cache

from .abc import FlagRetriever
from .country_flag import CountryFlagRetriever
from .lgbt_flag import LGBTFlagRetriever

import typing

retrievers: typing.List[FlagRetriever] = [CountryFlagRetriever(), LGBTFlagRetriever()]


@alru_cache
async def url_from_name(name, schema=None) -> typing.Optional[typing.Tuple[str, str, str]]:
    print(name, schema)
    for retriever in retrievers:
        if schema is None or retriever.schema == schema:
            ret = await retriever.url_from_name(name)
            if ret is not None:
                return ret + (str(retriever),)
