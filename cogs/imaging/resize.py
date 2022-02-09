import typing

import nextcord
from PIL import Image
from PIL.ImageDraw import ImageDraw
from nextcord.ext import commands


def center_resize(target: Image.Image, width, height):
    scale = max(width / target.width, height / target.height)

    new_width = target.width * scale
    new_height = target.height * scale

    x = (new_width - width) / 2
    y = (new_height - height) / 2

    box = [int(i) for i in (x, y, x + width, y + height)]

    return target.resize((int(new_width), int(new_height))).crop(box)


def stitch_flags(size, *flags: Image):
    mask = Image.new("L", size, 0)
    ret = Image.new("RGB", size, (0, 0, 0))

    mask_drawer = ImageDraw(mask)

    spacing = 1 / (len(flags) - 1) * size[0]

    def generate_point_for_idx(index):
        return index * spacing, size[1] if index % 2 == 0 else 0

    for idx, flag in enumerate(flags):
        points = [*generate_point_for_idx(idx - 1), *generate_point_for_idx(idx), *generate_point_for_idx(idx + 1)]

        mask_drawer.polygon(points, 255)

        flag = center_resize(flag, *size)

        ret.paste(flag, mask=mask)

        mask_drawer.rectangle((0, 0) + mask.size, 0)  # clear

    return ret


async def try_get_image(ctx: commands.Context, user: typing.Optional[nextcord.Member]):
    if user is not None:
        return await user.avatar.read()

    if ctx.message.reference is None:
        target = ctx.message
    else:
        target = await ctx.channel.fetch_message(ctx.message.reference.message_id)

    target: nextcord.Message

    if target.attachments:
        return await target.attachments[0].read()

    else:
        return await target.author.avatar.read()
