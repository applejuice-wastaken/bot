from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from render.scene import Scene

if TYPE_CHECKING:
    pass


class FlagOverlayScene(Scene):
    def __init__(self, user_image, mask, flag_image):
        super().__init__()

        self.flag_image = flag_image
        self.mask = mask
        self.user_image = user_image

    def lifecycle(self, t) -> typing.Union[typing.Optional[float], typing.Generator[float, float, float]]:
        flag = self.create_image(self.flag_image)
        mask = self.create_image(self.mask)
        user = self.create_image(self.user_image)

        self.width = user.width
        self.height = user.height
        self.min_duration = 0.1

        flag.mask = mask
        flag.mask_channel = "R"

        self.draw_object(user)
        self.draw_object(flag)

        return 0
