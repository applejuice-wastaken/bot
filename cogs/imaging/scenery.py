from __future__ import annotations

import enum
import math
import typing
from typing import TYPE_CHECKING

from PIL import Image
from render.scene import Scene

if TYPE_CHECKING:
    from render.objects.image import ImageComponent


class RotateDirection(enum.Enum):
    NO = enum.auto()
    CLOCKWISE = enum.auto()
    COUNTERCLOCKWISE = enum.auto()


class FlagOverlayScene(Scene):
    def __init__(self, user_image, mask, flag_image, *, rotate: RotateDirection = RotateDirection.NO, fps=60):
        super().__init__()

        self.flag_image = flag_image
        self.mask = mask
        self.user_image = user_image

        self.rotate = rotate
        self.min_frame_duration = 1 / fps

    def lifecycle(self, t) -> typing.Union[typing.Optional[float], typing.Generator[float, float, float]]:
        flag = self.create_image(self.flag_image)
        mask = self.create_image(self.mask)
        user: ImageComponent = self.create_image(self.user_image)

        self.width = user.width
        self.height = user.height

        flag.mask = mask
        flag.mask_channel = "R"
        flag.local_mask = False

        flag.transform.anchor = (flag.width / 2, flag.width / 2)
        flag.transform.position = (self.width / 2, self.height / 2)

        self.draw_object(user)
        self.draw_object(flag)

        if self.rotate != RotateDirection.NO:
            duration = 3

            if user.animated:
                duration = user.duration

            self.create_tween("linear", flag.defer.transform.angle, duration=duration, begin_value=0,
                              end_value=math.tau if self.rotate == RotateDirection.COUNTERCLOCKWISE else -math.tau)

        return 0


class HelicopterScene(Scene):
    def __init__(self, user_image, *, fps=60):
        super().__init__()

        self.user_image = user_image
        self.min_frame_duration = 1 / fps

    def lifecycle(self, t) -> typing.Union[typing.Optional[float], typing.Generator[float, float, float]]:
        image: ImageComponent = self.create_image(self.user_image)

        image.transform.anchor = (image.width / 2, image.height / 2)
        image.transform.scale = (100 / image.width, 100 / image.height)

        image.image_resample = Image.BICUBIC

        self.draw_object(image)

        self.width = 400
        self.height = 400

        image.transform.position = (200, 350)

        self.create_tween("easeInQuad", image.defer.transform.angle, duration=4, begin_value=0,
                          end_value=math.pi * 50)

        yield 4

        self.create_tween("linear", image.defer.transform.angle, duration=10, begin_value=0,
                          end_value=math.pi * 50 * 14 / 4)

        def pos_y(v):
            image.transform.position = (image.transform.position[0], v)

        self.create_tween("easeInOutQuad", pos_y, duration=10, begin_value=350, end_value=80)

        yield 5

        def pos_x(v):
            image.transform.position = (v, image.transform.position[1])

        self.create_tween("easeInQuad", pos_x, duration=5, begin_value=200, end_value=450)

        return 0
