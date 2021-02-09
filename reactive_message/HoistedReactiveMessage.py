from abc import ABC

from reactive_message.ReactiveMessage import ReactiveMessage


class HoistedReactiveMessage(ReactiveMessage, ABC):
    def __init__(self, cog, channel):
        super().__init__(cog, channel)

        self.messages_until_resend = 10

    async def on_message(self, message):
        self.messages_until_resend -= 1
        if self.messages_until_resend <= 0:
            await self.send_from_dict(self.current_render)
            self.messages_until_resend = 10
