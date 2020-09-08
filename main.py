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
                if line.endswith("\n"):
                    line = line[:-1]
                self.load_extension(f"cogs.{line}")
                print(f"loaded {line}")


if __name__ == "__main__":
    token = os.getenv("TOKEN", None)
    prefix = os.getenv("PREFIX", None)

    if token is None or prefix is None:
        # probably local

        with open("config.json") as f:
            t = json.loads(f.read())
            token = t["token"]
            prefix = t["prefix"]
    else:
        # probably in the server

        keep_alive()

    DiscordBot(prefix).run(token)
