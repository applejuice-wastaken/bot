import typing

import nextcord
from nextcord import SlashOption
from nextcord.ext import commands
from phrase_reference_builder.pronouns import Pronoun, PronounType, default_repository

from etcetra.interops import CommandInterop, ResponseKind, ResponsePrivacyKind
from etcetra.pronouns import convert_string_to_pronoun, get_pronouns_from_member

if typing.TYPE_CHECKING:
    pass

PRONOUN_FAILURE = f"""
Could not Identify pronoun
Ensure that your pronoun follows one of this schemas
    a/b/c/d/e => a/b/c/d/e
    a/c/e => a/a/c/c/e
    a/bself => a/a/a's/a's/aself
    emoji/emoji => emoji/emoji/emoji's/emoji's/emojiself
    a/b => <pronoun> (for normatives/some neopronouns)
"""


async def impl_pronoun_get(resp: CommandInterop, user):
    pronouns = get_pronouns_from_member(user)

    if pronouns:
        pronouns_lines = []
        for pronoun in pronouns:
            pronouns_lines.append(f"{str(pronoun)} ({pronoun.pronoun_type.name.replace('_', ' ').title()})")

        pronoun_str = "\n".join(pronouns_lines)

        embed = nextcord.Embed(title=f"{user.name}'s detected pronouns", description=pronoun_str)
        await resp.respond(embed=embed, privacy=ResponsePrivacyKind.PRIVATE_IF_POSSIBLE)

    else:
        await resp.respond("*No pronouns detected*", kind=ResponseKind.FAILURE)


async def impl_pronoun_test(resp: CommandInterop, raw: str):
    p = convert_string_to_pronoun(resp.author.name, raw)

    if p is None:
        await resp.respond(PRONOUN_FAILURE, kind=ResponseKind.FAILURE)

    else:
        lines = []
        for attr in (*Pronoun.get_morpheme_names(), "pronoun_type", "person_class", "collective"):
            value = getattr(p, attr)

            if isinstance(value, PronounType):
                display = value.name.lower().replace("_", " ")

            else:
                display = repr(value)

            lines.append(f"    **{attr.replace('_', ' ')}:** {display}")

        await resp.respond("here's what I recognise:\n" + "\n".join(lines))


class Pronouns(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    # groups

    @nextcord.slash_command(name="pronouns")
    async def s_pronoun_root(self, interaction):
        pass

    # pronoun get command

    @commands.group(name="pronouns", invoke_without_command=True)
    async def c_pronoun_get(self, ctx, user: nextcord.Member = None):
        """Gets the detected pronoun's from a user"""

        if user is None:
            user = ctx.author

        await impl_pronoun_get(CommandInterop.from_command(ctx), user)

    @s_pronoun_root.subcommand(name="get", description="Gets the detected pronoun's from an user")
    async def s_pronoun_get(self, interaction,
                            user: nextcord.Member =
                            SlashOption(required=False, description="The user you want to fetch the pronouns from")):

        if user is None:
            user = interaction.user

        await impl_pronoun_get(CommandInterop.from_slash_interaction(interaction), user)

    # pronoun test command

    @c_pronoun_get.command(name="test")
    async def c_pronoun_test(self, ctx, p_str):
        """Tests if the bot can detect a pronoun's presentation"""
        await impl_pronoun_test(CommandInterop.from_command(ctx), p_str)

    @s_pronoun_root.subcommand(name="test", description="Tests if the bot can detect a pronoun's presentation")
    async def s_pronoun_test(self, interaction, pronoun=SlashOption("pronoun", description="The pronoun")):
        """Tests a pronoun's representation"""
        pronoun: str
        await impl_pronoun_test(CommandInterop.from_slash_interaction(interaction), pronoun)

    @s_pronoun_test.on_autocomplete("pronoun")
    async def s_pronoun_test_auto_pronoun(self, interaction, pronoun: str):
        all_pronouns = default_repository.custom_pronouns | default_repository.main_pronouns

        filtered = set(str(p) for p in all_pronouns if str(p).startswith(pronoun))

        await interaction.response.send_autocomplete(list(filtered))


def setup(bot):
    bot.add_cog(Pronouns(bot))
