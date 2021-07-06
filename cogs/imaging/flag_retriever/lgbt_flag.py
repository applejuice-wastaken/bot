import typing
import urllib.parse

import aiohttp

from . import Flag
from .abc import FlagRetriever


class LGBTFlagRetriever(FlagRetriever):
    @property
    def schema(self):
        return "lgbt"

    async def get_flag(self, name) -> typing.Optional[Flag]:
        async with aiohttp.ClientSession() as session:

            async with session.get(f"https://lgbta.wikia.org/api.php?action=query&"
                                   f"list=search&srsearch={urllib.parse.quote(name)}"
                                   f"&format=json") as search_response:
                json_content = await search_response.json()
                pages = json_content["query"]["search"]

                if pages:
                    # there's results; get article image
                    first_page_id = pages[0]["pageid"]
                    first_page_title = pages[0]["title"]

                    async with session.get(f"https://lgbta.wikia.org/api.php?action=imageserving&"
                                           f"wisId={first_page_id}&format=json") as image_response:
                        json_content = await image_response.json()

                        if "error" not in json_content and "image" in json_content:
                            return Flag(json_content["image"]["imageserving"], first_page_title, str(self),
                                        is_remote=True)

                        else:
                            # article has no thumbnail for some reason
                            async with session.get(f"https://lgbta.wikia.org/api.php?action=query&prop=images&titles="
                                                   f"{urllib.parse.quote(first_page_title)}&format=json") as content_response:

                                json_content = await content_response.json()

                                if "error" not in json_content and\
                                        "images" in json_content["query"]["pages"][str(first_page_id)]:
                                    images = json_content["query"]["pages"][str(first_page_id)]["images"]

                                    if images:
                                        image_title = images[0]["title"]
                                        async with session.get(f"https://lgbta.wikia.org/api.php?action=query&titles="
                                                               f"{urllib.parse.quote(image_title)}&prop=imageinfo"
                                                               f"&iiprop=url&format=json") as alternative_image_response:
                                            json_content = await alternative_image_response.json()
                                            print(json_content)
                                            pages = json_content["query"]["pages"]
                                            page = pages[list(pages)[0]]
                                            return Flag(page["imageinfo"][0]["url"], first_page_title,
                                                        str(self), is_remote=True)

        return None

    def __str__(self):
        return "lgbt wiki"
