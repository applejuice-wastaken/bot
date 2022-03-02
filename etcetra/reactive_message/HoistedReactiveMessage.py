from abc import ABC

from .ReactiveMessage import ReactiveMessage


class HoistedReactiveMessage(ReactiveMessage, ABC):
    def __init__(self, cog, channel):
        super().__init__(cog, channel)

        self.messages_until_resend = 10

    async def process_message(self, message):
        self.messages_until_resend -= 1
        if self.messages_until_resend <= 0:
            await self.send_from_dict(self.current_displaying_render)
            self.messages_until_resend = 10
