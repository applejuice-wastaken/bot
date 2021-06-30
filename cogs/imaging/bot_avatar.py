import datetime
import os

from PIL import Image

from cogs.imaging.flag_retriever import get_flag
from .resize import center_resize


def path(*args):
    return os.path.join(os.path.dirname(__file__), *args)


async def get_new_avatar(cog):
    original: Image.Image = await cog.execute(Image.open, path("quantum.png"))

    now = datetime.datetime(year=2021, month=5, day=29)

    if now.month in (5, 6, 7):
        # happy pride month

        flag = await get_flag("gay")

        if flag is None:
            return original

        flag_image = await flag.open()
        flag_image: Image.Image
        flag_image = center_resize(flag_image, *original.size)

        blending = None

        if now.month == 7:
            # transition to default
            blending = max(1 - (now.day / 10), 0)

        elif now.month == 5:
            # transition to flag
            blending = max((now.day - 21) / 10, 0)

        if blending is None:
            original.paste(flag_image, mask=original)
        else:
            with_flag = Image.composite(flag_image, original, mask=original).convert("RGBA")
            original = Image.blend(original, with_flag, blending)

    original.save("img.png")

    return original
