from __future__ import annotations

import inspect
import typing

import discord
from discord.ext import commands
from phrase_reference_builder.build import PhraseBuilder
from phrase_reference_builder.types import MaybeReflexive

from .argument import RelativeMemberConverter
from .fragments import author, condition

if typing.TYPE_CHECKING:
    pass


def interaction_command_factory(name, *,
                                connotation=None,
                                image_processor=None,
                                normal: list,
                                reject: list,
                                condition_rejected: list =
                                author + " could not do this to " + MaybeReflexive(author, condition),
                                mutual=True,
                                condition_predicate=lambda _, __: True):
    async def command(self, ctx, *users: RelativeMemberConverter):

        message = await make_response(self, ctx, *users)

        if message is not None:
            async def unload():
                await message.delete()

            ctx.bot.get_cog("Uninvoke").create_unload(ctx.message, unload)

    command.__doc__ = f"executes a {name} action towards selected users, if allowed"

    async def make_response(self, ctx, *users: discord.Member):
        users: typing.List[discord.Member] = list(users)

        if mutual and not user_accepts(ctx.author, name, "thing"):
            return await ctx.send(f"But you don't like that")

        if ctx.message.reference is not None:
            referenced: discord.Message
            referenced = (ctx.message.reference.cached_message or
                          await ctx.message.channel.fetch_message(ctx.message.reference.message_id))

            users.append(referenced.author)

        allowed = []
        role_denied = []
        condition_denied = []

        for user in users:
            # noinspection PyTypeChecker
            if user_accepts(user, name, "thing"):
                if condition_predicate(ctx.author, user):
                    allowed.append(user)
                else:
                    condition_denied.append(user)
            else:
                role_denied.append(user)

        if not users:
            return await ctx.send("No users", allowed_mentions=discord.AllowedMentions.none())

        title_baking = []

        if allowed:
            title_baking.extend(normal)

        description_baking = []

        if allowed and (role_denied or condition_denied):
            description_baking.append("however")

        if role_denied:
            description_baking.extend(reject)

        if condition_denied:
            description_baking.extend(condition_rejected)

        with PhraseBuilder() as builder:
            builder.referenced.append(builder.convert_to_entity_collection(ctx.bot.user)[0])
            title = builder.build(title_baking, speaker=ctx.bot.user,
                                  deferred={"action_author": ctx.author,
                                            "valid": allowed,
                                            "rejected": role_denied,
                                            "condition": condition_denied})

            if title == "":
                title = discord.Embed.Empty

            elif len(title) > 256:
                return await ctx.message.reply(embed=discord.Embed(title="(ಠ_ಠ)"),
                                               allowed_mentions=discord.AllowedMentions.none())

            description = builder.build(description_baking, speaker=ctx.bot.user,
                                        deferred={"action_author": ctx.author,
                                                  "valid": allowed,
                                                  "rejected": role_denied,
                                                  "condition": condition_denied})

            if connotation is not None and \
                    ((not role_denied and not condition_denied) and ctx.bot.user in allowed):
                if connotation:
                    self.karma += 1

                    if self.karma > 5:
                        description += " :D"

                    else:
                        description += " :)"

                else:
                    self.karma -= 1

                    if self.karma < -5:
                        description += " :(((((((("

                    else:
                        description += " :("

            if description == "":
                description = discord.Embed.Empty

        embed = discord.Embed(title=title, description=description)

        if image_processor is not None and len(allowed) > 0:
            if callable(image_processor):
                image = await image_processor()

            else:
                image = image_processor

            embed.set_image(url=image)

        return await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    command = commands.guild_only()(commands.Command(command, name=name))

    # inject command into class by putting it into a variable in it's frame
    inspect.currentframe().f_back.f_locals[f"_command_{name}"] = command


def user_accepts(member, *actions):
    if isinstance(member, discord.User) or member.discriminator == "0000":
        return True

    for action in actions:
        role = discord.utils.get(member.roles, name=f"no {action}")

        allowed = role is None

        if not allowed:
            return False
    return True
