import functools
import inspect
import json
import os

import nextcord
from nextcord import PartialEmoji
from nextcord.ext import commands
from nextcord.message import convert_emoji_reaction

try:
    with open("config.json") as f:
        t = json.loads(f.read())
except FileNotFoundError:
    t = {}


def get_env_value(value: str):
    ret = os.getenv(value, None)
    if ret is None:
        ret = t[value]
    return ret


def _listener_bind(method, self, obj):
    for attr, func in inspect.getmembers(obj, inspect.ismethod):
        if attr.startswith("on_"):
            getattr(self, method)(func, attr)


class DiscordBot(commands.Bot):
    get_env_value = staticmethod(get_env_value)

    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)

        with open("cogs/cogs") as cogs_file:
            for line in cogs_file.readlines():
                if line.endswith("\n"):
                    line = line[:-1]
                self.load_extension(f"cogs.{line}")
                print(f"loaded {line}")

    async def on_ready(self):
        await self.change_presence(activity=nextcord.Game(name=f"prefix {self.command_prefix}command"))

    def dispatch(self, event_name, *args, **kwargs):
        super().dispatch("event", event_name, *args, **kwargs)
        super().dispatch(event_name, *args, **kwargs)

    async def choice(self, message, *reactions, check=lambda ev: True) -> PartialEmoji:
        for reaction in reactions:
            await message.add_reaction(reaction)

        def c(ev):
            p: PartialEmoji = ev.emoji
            if not any(convert_emoji_reaction(p) == convert_emoji_reaction(r) for r in reactions):
                return False

            if ev.message_id == message.id and self.user.id != ev.user_id:
                return check(ev)

        return (await self.wait_for("raw_reaction_add", check=c, timeout=40)).emoji

    async def get_webhook_for_channel(self, channel):
        for wb in await channel.webhooks():
            if wb.name == "qc":
                return wb
        else:
            try:
                return await channel.create_webhook(name="qc")
            except nextcord.Forbidden:
                return None

    add_listener_object = functools.partialmethod(_listener_bind, "add_listener")
    remove_listener_object = functools.partialmethod(_listener_bind, "remove_listener")


if __name__ == "__main__":
    token = get_env_value("token")
    prefix = get_env_value("prefix")

    intents = nextcord.Intents.default()

    DiscordBot(prefix, help_command=commands.MinimalHelpCommand(), case_insensitive=True, intents=intents).run(token)
