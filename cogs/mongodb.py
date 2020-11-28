import discord
import motor.motor_asyncio
from discord.ext import commands

class MongoDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        mongodb = bot.get_env_value("mongodb")

        self._database = motor.motor_asyncio.AsyncIOMotorClient(mongodb).botDatabase

    def __getattr__(self, item):
        if item.startswith("get_"):
            collection_name = item[4:]

            async def _(record_id):
                return await self._database[collection_name].find({"_id": record_id}).next()

            return _


def setup(bot):
    bot.add_cog(MongoDB(bot))
