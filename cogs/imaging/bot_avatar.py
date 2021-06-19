import datetime
import os
from io import BytesIO

import aiofiles
from PIL import Image

from cogs.imaging.flag_retriever import get_flag

from .resize import center_resize

def path(*args):
    return os.path.join(os.path.dirname(__file__), *args)

async def get_new_avatar(cog):
    original: Image.Image = await cog.execute(Image.open, path("quantum.png"))

    now = datetime.datetime.now()

    if now.month == 6:
        # happy pride month

        flag = await get_flag("gay")

        if flag is None:
            return original

        flag_image = await flag.open()
        flag_image: Image.Image
        flag_image = center_resize(flag_image, *original.size)

        original.paste(flag_image, mask=original)

    return original
