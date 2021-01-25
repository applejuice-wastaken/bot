import discord
from discord.abc import Messageable


class GamePlayer(Messageable):
    async def _get_channel(self):
        return self.bound_channel

    async def send(self, *args, **kwargs):
        if self.able_to_send_messages:
            try:
                await super(GamePlayer, self).send(*args, **kwargs)
            except:
                self.able_to_send_messages = False

    def __init__(self, user, bound_channel):
        self.bound_channel = bound_channel
        self.user = user
        self.able_to_send_messages = True
        self.game_instance = None  # it is provided later

    def __getattr__(self, item):
        return getattr(self.user, item)
