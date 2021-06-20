import random

import discord
import humanize
from discord.ext import commands

from util.human_join_list import human_join_list
from util.pronouns import figure_pronouns


class InfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        pronouns = await figure_pronouns(user, return_default=False, return_multiple=True)

        if pronouns is None:
            description = discord.Embed.Empty
        else:
            if len(pronouns) < 5:
                pronoun_str = human_join_list([str(pronoun) for pronoun in pronouns],
                                              analyse_contents=False, end_join=' or ')
            else:
                pronoun_str = "some pronouns"

            description = f"I use {pronoun_str} :{random.choice(')]D>')}"

        embed = discord.Embed(title=user.display_name, description=description)

        embed.set_thumbnail(url=user.avatar_url)

        embed.add_field(name="Time I was created", value=date(user.created_at))
        embed.add_field(name="Time I joined this server", value=date(user.joined_at))
        embed.add_field(name="My ID", value=str(user.id), inline=False)

        roles = [role for role in user.roles if role.guild.default_role != role]
        roles_str = human_join_list([role.mention for role in roles])

        embed.add_field(name="Roles", value=f"{len(roles)} roles\n{roles_str}", inline=False)

        await ctx.send(embed=embed)

def date(d):
    return f"At {humanize.naturaldate(d)} (or {humanize.naturaltime(d)})"

def setup(bot):
    bot.add_cog(InfoCog(bot))
