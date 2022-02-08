import random

import nextcord
import humanize
from nextcord import SlashOption, Interaction
from nextcord.ext import commands

from util.interops import CommandInterop, ResponsePrivacyKind
from util.pronouns import get_pronouns_from_member, convert_string_to_pronoun


class InfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    async def impl_user(self, resp: CommandInterop, user: nextcord.Member):
        """Gets info of an user"""

        pronouns = get_pronouns_from_member(user)

        if pronouns is None:
            description = nextcord.Embed.Empty
        else:
            if len(pronouns) < 20:
                pronouns_lines = []
                for pronoun in pronouns:
                    pronouns_lines.append(f"{str(pronoun)} ({pronoun.pronoun_type.name.replace('_', ' ').title()})")

                pronoun_str = "\n" + "\n".join(pronouns_lines) + "\n"
            else:
                pronoun_str = "a lot of pronouns"

            description = f"I use {pronoun_str} :{random.choice(')]D>')}"

        embed = nextcord.Embed(title=user.display_name, description=description)

        embed.set_thumbnail(url=user.avatar.url)

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

        await resp.respond(embed=embed, privacy=ResponsePrivacyKind.PRIVATE_IF_POSSIBLE)

    async def detects_role(self, role):
        return (convert_string_to_pronoun("", role.name)) is not None

    # user info command

    @nextcord.slash_command(name="user", description="Get information about someone")
    async def s_user(self, interaction: Interaction, user: nextcord.Member = SlashOption(required=False)):

        if user is None:
            user = interaction.user

        await self.impl_user(await CommandInterop.from_slash_interaction(interaction), user)

    @commands.command(name="user")
    async def c_user(self, ctx, user: nextcord.Member = None):
        """Get information about someone"""

        if user is None:
            user = ctx.author

        await self.impl_user(await CommandInterop.from_command(ctx), user)


def date(d):
    return f"At {humanize.naturaldate(d)} (or {humanize.naturaltime(d.replace(tzinfo=None))})"


def setup(bot):
    bot.add_cog(InfoCog(bot))
