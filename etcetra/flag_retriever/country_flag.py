import difflib
import typing

import aiohttp

from . import Flag
from .abc import FlagRetriever


class CountryFlagRetriever(FlagRetriever):
    @property
    def schema(self):
        return "country"

    def __init__(self):
        self._codes: typing.Optional[dict] = None
        self._codes_inverted: typing.Optional[dict] = None

    async def get_codes(self) -> dict:
        if self._codes is None:
            async with aiohttp.request("GET", f"https://flagcdn.com/en/codes.json") as code_response:
                self._codes = await code_response.json()
                self._codes = {k.lower(): v for k, v in self._codes.items()}

        return self._codes

    async def get_inverted_codes(self) -> dict:
        if self._codes_inverted is None:
            codes = await self.get_codes()
            self._codes_inverted = {v: k for k, v in codes.items()}

        return self._codes_inverted

    async def code_from_name(self, name) -> typing.Optional[str]:
        return (await self.get_inverted_codes()).get(name, None)

    # noinspection PyTypeChecker
    async def get_flag(self, name) -> typing.Optional[Flag]:
        name = name.lower()
        codes = await self.get_codes()
        if name in codes:
            return Flag(f"https://flagcdn.com/w320/{name}.png", codes[name], str(self), is_remote=True)
        else:
            match = difflib.get_close_matches(name, codes.values(), 1, 0.8)
            if match:
                code = await self.code_from_name(match[0])
                return Flag(f"https://flagcdn.com/w320/{code}.png", match[0], str(self), is_remote=True)

    async def search(self, name) -> typing.Set[str]:
        return set(n for n in (await self.get_inverted_codes()).keys() if n.startswith(name))

    def __str__(self):
        return "flagcdn"
