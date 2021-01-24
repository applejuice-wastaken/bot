import os
import json
import discord
import logging

from keep_alive import keep_alive

from discord.ext import commands

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


class DiscordBot(commands.Bot):
    get_env_value = staticmethod(get_env_value)

    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)

        self.load_extension("jishaku")

        with open("cogs/cogs") as cogs_file:
            for line in cogs_file.readlines():
                if line.endswith("\n"):
                    line = line[:-1]
                self.load_extension(f"cogs.{line}")
                print(f"loaded {line}")

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name=f"prefix {self.command_prefix}command"))

    def dispatch(self, event_name, *args, **kwargs):
        super().dispatch("event", event_name, *args, **kwargs)
        super().dispatch(event_name, *args, **kwargs)

    async def choice(self, message, *reactions, check=lambda r, u: True):
        for reaction in reactions:
            await message.add_reaction(reaction)

        def c(r, u):
            if r.message.id == message.id and self.user.id != u.id:
                return check(r, u)

        return await self.wait_for("reaction_add", check=c, timeout=40)

    async def get_webhook_for_channel(self, channel):
        for wb in await channel.webhooks():
            if wb.name == "qc":
                return wb
        else:
            try:
                return await channel.create_webhook(name="qc")
            except discord.Forbidden:
                return None


if __name__ == "__main__":
    token = get_env_value("token")
    prefix = get_env_value("prefix")

    if str(get_env_value("run_keep_alive")) == "True":
        keep_alive()

    DiscordBot(prefix).run(token)
