import nextcord
from nextcord import Interaction
from nextcord.ext import commands


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="doggo")
    async def c_dog(self, ctx):
        """doggo"""
        await ctx.send("doggo")

    @nextcord.slash_command(name="doggo", description="doggo")
    async def s_dog(self, interaction: Interaction):
        await interaction.send("doggo")

    @commands.is_owner()
    @commands.command(name="wb")
    async def send_webhook(self, ctx, name, av, *, content):
        await ctx.message.delete()
        webhook = await self.bot.get_webhook_for_channel(ctx.channel)

        if webhook is not None:
            await webhook.send(content, username=name, avatar_url=av if av.startswith("http") else None)


def setup(bot):
    bot.add_cog(Fun(bot))
