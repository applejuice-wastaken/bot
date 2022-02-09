from __future__ import annotations

import enum
import math
import typing
from typing import TYPE_CHECKING

from render.objects.image import ImageComponent
from render.scene import Scene

if TYPE_CHECKING:
    pass


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
