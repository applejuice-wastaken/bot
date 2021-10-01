import random

import discord
import humanize
from discord.ext import commands

from util.pronouns import get_pronouns_from_member, convert_string_to_pronoun


class InfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    async def detects_role(self, role):
        return (convert_string_to_pronoun("", role.name)) is not None

    @commands.command()
    async def info(self, ctx, user: discord.Member = None):
        if user is not None:
            return await self.user(ctx, user)

        embed = discord.Embed(title="Hello it's me, Quantum", description="Made with discord.py and such")

        embed.set_thumbnail(url=self.bot.user.avatar_url)

        embed.add_field(name="What even are you", value="I'm a culmination of an idiot named applejuice "
                                                        "making bots since 2017", inline=False)

        embed.add_field(name="Why do you exist", value="For some reason applejuice likes to make stuff", inline=False)

        embed.add_field(name="Why that avatar", value="Applejuice likes it and it also matches their "
                                                      "ominous art style", inline=False)

        embed.add_field(name="You're not a good bot", value="eh", inline=False)

        embed.add_field(name="You're a good bot", value="You liar you said I wasn't just now", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def user(self, ctx, user: discord.Member = None):
        """Gets info of an user"""

        if user is None:
            user = ctx.author

        if user.id == self.bot.user.id:
            return await self.info(ctx)

        pronouns = get_pronouns_from_member(user)

        if pronouns is None:
            description = discord.Embed.Empty
        else:
            if len(pronouns) < 20:
                pronouns_lines = []
                for pronoun in pronouns:
                    pronouns_lines.append(f"{str(pronoun)} ({pronoun.pronoun_type.name.replace('_', ' ').title()})")

                pronoun_str = "\n" + "\n".join(pronouns_lines) + "\n"
            else:
                pronoun_str = "a lot of pronouns"

            description = f"I use {pronoun_str} :{random.choice(')]D>')}"

        embed = discord.Embed(title=user.display_name, description=description)

        embed.set_thumbnail(url=user.avatar_url)

        embed.add_field(name="Time I was created", value=date(user.created_at))
        embed.add_field(name="Time I joined this server", value=date(user.joined_at))
        embed.add_field(name="My ID", value=str(user.id), inline=False)

        detected_roles = []
        other_roles = []

        for role in user.roles:
            if user.guild.default_role == role:
                continue

            for cog_name, cog in self.bot.cogs.items():
                if hasattr(cog, "detects_role") and await cog.detects_role(role):
                    detected_roles.append(role)
                    break

            else:
                other_roles.append(role)

        if other_roles:
            embed.add_field(name="Roles", value=" ".join(r.mention for r in other_roles), inline=False)

        if detected_roles:
            embed.add_field(name="Special Roles", value=" ".join(r.mention for r in detected_roles), inline=False)

        await ctx.send(embed=embed)


def date(d):
    return f"At {humanize.naturaldate(d)} (or {humanize.naturaltime(d)})"


def setup(bot):
    bot.add_cog(InfoCog(bot))
