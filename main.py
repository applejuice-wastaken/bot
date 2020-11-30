import os
import json
import discord
import logging

from keep_alive import keep_alive

from discord.ext import commands

with open("config.json") as f:
    t = json.loads(f.read())


def get_env_value(value: str):
    ret = os.getenv(value, None)
    if ret is None:
        ret = t[value]
    return ret


class DiscordBot(commands.Bot):
    get_env_value = lambda self, *args, **kwargs: get_env_value(*args, **kwargs)

    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)

        self.load_extension("jishaku")

        with open("cogs/cogs") as cogs_file:
            for line in cogs_file.readlines():
                if line.endswith("\n"):
                    line = line[:-1]
                self.load_extension(f"cogs.{line}")
                print(f"loaded {line}")

    def dispatch(self, event_name, *args, **kwargs):
        super().dispatch("event", event_name, *args, **kwargs)
        super().dispatch(event_name, *args, **kwargs)


if __name__ == "__main__":
    token = get_env_value("token")
    prefix = get_env_value("prefix")

    if str(get_env_value("run-keep-alive")) == "True":
        keep_alive()

    DiscordBot(prefix).run(token)
