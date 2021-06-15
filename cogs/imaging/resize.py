from PIL import Image


def center_resize(target: Image.Image, width, height):
    scale = max(width / target.width, height / target.height)

    new_width = target.width * scale
    new_height = target.height * scale

    x = (new_width - width) / 2
    y = (new_height - height) / 2

    box = [int(i) for i in (x, y, x + width, y + height)]

    return target.resize((int(new_width), int(new_height))).crop(box)