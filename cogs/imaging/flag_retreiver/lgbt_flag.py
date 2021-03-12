import typing

import aiohttp

import difflib

from .abc import FlagRetriever


class LGBTFlagRetriever(FlagRetriever):
    @property
    def schema(self):
        return "lgbt"

    async def url_from_name(self, name) -> typing.Optional[typing.Tuple[str, str]]:
        async with aiohttp.request("GET", f"https://lgbta.wikia.org/api.php?action=query&"
                                          f"list=search&srsearch={name}&format=json") as search_response:
            json_content = await search_response.json()
            pages = json_content["query"]["search"]

            if pages:
                # there's results; get article image
                first_page_id = pages[0]["pageid"]

                async with aiohttp.request("GET", f"https://lgbta.wikia.org/api.php?action=imageserving&"
                                                  f"wisId={first_page_id}&format=json") as image_response:
                    json_content = await image_response.json()

                    return json_content["image"]["imageserving"], pages[0]["title"]

        return None

    def __str__(self):
        return "lgbt wiki"
