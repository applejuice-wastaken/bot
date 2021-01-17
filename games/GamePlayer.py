from discord.abc import Messageable


class GamePlayer(Messageable):
    async def _get_channel(self):
        return self.bound_channel

    def __init__(self, user, bound_channel):
        self.bound_channel = bound_channel
        self.user = user

    def __getattr__(self, item):
        return getattr(self.user, item)
