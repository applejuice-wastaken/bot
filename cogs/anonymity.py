import discord
from discord.ext import commands
import aiohttp
import json
from util.requires_cog import requires_cog


class Anonymity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ask_name(self, recipient):
        while True:
            initial_embed = discord.Embed(title="Select method",
                                          description="✏: Customized name\n🤖: Automatically generated name")
            message = await recipient.send(embed=initial_embed)
            reaction, user = await self.bot.choice(message, "✏", "🤖")

            if reaction.emoji == "✏":
                message = await recipient.send("Send your fake name...")

                def check(m):
                    return message.channel.id == m.channel.id

                selected_name = (await self.bot.wait_for("message", check=check)).content
            else:
                async with aiohttp.request("GET", "https://api.namefake.com/") as response:
                    selected_name = json.loads(await response.read())["name"].split(" ")[0]

            initial_embed = discord.Embed(title=f"Your fake name will be {selected_name}",
                                          description="Keep?")
            message = await recipient.send(embed=initial_embed)

            reaction, user = await self.bot.choice(message, "✅", "❌")

            if reaction.emoji == "✅":
                return selected_name

    @requires_cog("Firestore")
    @commands.dm_only()
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.command(name="atalk")
    async def talk(self, ctx, channel_id: int, *, content):
        print(ctx.me)
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            await ctx.send("That channel does not exist")
            return

        if not isinstance(channel, discord.TextChannel):
            await ctx.send("That channel is not a text channel")
            return

        if not channel.permissions_for(channel.guild.get_member(ctx.me.id)).manage_webhooks:
            await ctx.send("I don't have sufficient permissions to do this")
            return

        cog = self.bot.get_cog("Firestore")
        channel_obj, channel_document = await cog.get("guild", channel.guild.id)

        if str(channel.id) not in channel_obj["channel_flags"] or \
                not (channel_obj["channel_flags"][str(channel.id)] & 1):
            await ctx.send("That channel does not support anonymity")
            return

        user_obj, user_document = await cog.get("user", ctx.author.id)

        if user_obj["faked_name"] is None:
            await ctx.send("You don't have a fake name associated with account")
            selected_name = await self.ask_name(ctx)
            user_obj["faked_name"] = selected_name
            await user_document.set(user_obj)

        for wb in await channel.webhooks():
            if wb.name == "qc":
                webhook = wb
                break
        else:
            webhook = await channel.create_webhook(name="qc")

        await webhook.send(content, username=f"Anon. {user_obj['faked_name']}")
        await ctx.send("Sent")


def setup(bot):
    bot.add_cog(Anonymity(bot))
