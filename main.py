import os
import json
import discord
import logging
from keep_alive import keep_alive

from discord.ext import commands

class DiscordBot(commands.Bot):
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)

        with open("cogs/cogs") as cogs_file:
            for line in cogs_file.readlines():
                self.load_extension(f"cogs.{line}")
                print(f"loaded {line}")


if __name__ == "__main__":
    token = os.getenv("TOKEN", None)
    prefix = os.getenv("PREFIX", None)

    if token is None or prefix is None:
        with open("config.json") as f:
            token = json.loads(f.read())["token"]
            prefix = json.loads(f.read())["prefix"]

    keep_alive()

    DiscordBot(prefix).run(token)
