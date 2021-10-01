from __future__ import annotations

import typing

import discord
from discord.ext import commands
from phrase_reference_builder.build import PhraseBuilder, Entity
from phrase_reference_builder.pronouns import Pronoun, PronounType
from phrase_reference_builder.types import DeferredReference

from util.pronouns import convert_string_to_pronoun, get_pronouns_from_member

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


class Pronouns(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.group(name="pronoun", invoke_without_command=True)
    async def main(self, ctx):
        """sends a message"""

        pronouns = get_pronouns_from_member(ctx.author)

        if pronouns:
            pronouns_lines = []
            for pronoun in pronouns:
                pronouns_lines.append(f"{str(pronoun)} ({pronoun.pronoun_type.name.replace('_', ' ').title()})")

            pronoun_str = "\n".join(pronouns_lines)

            embed = discord.Embed(title=f"{ctx.author.name}'s detected pronouns", description=pronoun_str)
            await ctx.send(embed=embed)

        else:
            await ctx.send("*No detected pronouns*")

    @main.command()
    async def test(self, ctx, p_str):
        p = convert_string_to_pronoun(ctx.author, p_str)

        if p is None:
            await ctx.send(PRONOUN_FAILURE)

        else:
            lines = []
            for attr in (*Pronoun.get_morpheme_names(), "pronoun_type", "person_class", "collective"):
                value = getattr(p, attr)

                if isinstance(value, PronounType):
                    display = value.name.lower().replace("_", " ")

                else:
                    display = repr(value)

                lines.append(f"    **{attr.replace('_', ' ')}:** {display}")

            await ctx.send("here's what I recognise:\n" + "\n".join(lines))


def setup(bot):
    bot.add_cog(Pronouns(bot))
