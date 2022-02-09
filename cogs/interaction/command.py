import inspect
import typing

import nextcord
from nextcord import Interaction
from nextcord.ext import commands
from phrase_reference_builder.build import PhraseBuilder
from phrase_reference_builder.types import MaybeReflexive

from util.interops import CommandInterop, ResponseKind
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
    async def impl_interaction(resp: CommandInterop, cog, author_user, *users: nextcord.Member):
        users: typing.List[nextcord.Member] = list(users)

        if mutual and not user_accepts(author_user, name, "thing"):
            return await resp.respond(f"But you don't like that", kind=ResponseKind.FAILURE)

        allowed = []
        role_denied = []
        condition_denied = []

        for user in users:
            # noinspection PyTypeChecker
            if user_accepts(user, name, "thing"):
                if condition_predicate(author_user, user):
                    allowed.append(user)
                else:
                    condition_denied.append(user)
            else:
                role_denied.append(user)

        if not users:
            return await resp.respond("No users", allowed_mentions=nextcord.AllowedMentions.none())

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
            builder.referenced.append(builder.convert_to_entity_collection(cog.bot.user)[0])
            title = builder.build(title_baking, speaker=cog.bot.user,
                                  deferred={"action_author": author_user,
                                            "valid": allowed,
                                            "rejected": role_denied,
                                            "condition": condition_denied})

            if title == "":
                title = nextcord.Embed.Empty

            elif len(title) > 256:
                return await resp.respond(embed=nextcord.Embed(title="(ಠ_ಠ)"),
                                          allowed_mentions=nextcord.AllowedMentions.none())

            description = builder.build(description_baking, speaker=cog.bot.user,
                                        deferred={"action_author": author_user,
                                                  "valid": allowed,
                                                  "rejected": role_denied,
                                                  "condition": condition_denied})

            if connotation is not None and \
                    ((not role_denied and not condition_denied) and cog.bot.user in allowed):
                if connotation:
                    cog.karma += 1

                    if cog.karma > 5:
                        description += " :D"

                    else:
                        description += " :)"

                else:
                    cog.karma -= 1

                    if cog.karma < -5:
                        description += " :(((((((("

                    else:
                        description += " :("

            if description == "":
                description = nextcord.Embed.Empty

        embed = nextcord.Embed(title=title, description=description)

        if image_processor is not None and len(allowed) > 0:
            if callable(image_processor):
                image = await image_processor()

            else:
                image = image_processor

            embed.set_image(url=image)

        return await resp.respond(embed=embed, allowed_mentions=nextcord.AllowedMentions.none())

    async def c_command(self, ctx, *users: RelativeMemberConverter):
        users = list(users)

        if ctx.message.reference is not None:
            referenced: nextcord.Message
            referenced = (ctx.message.reference.cached_message or
                          await ctx.message.channel.fetch_message(ctx.message.reference.message_id))

            users.append(referenced.author)

        await impl_interaction(CommandInterop.from_command(ctx), self, ctx.author, *users)

    async def s_command(self, interaction: Interaction, user: nextcord.Member):
        await impl_interaction(await CommandInterop.from_slash_interaction(interaction), self, interaction.user, user)

    c_command.__doc__ = f"executes a {name} action towards selected users, if allowed"

    c_command = commands.guild_only()(commands.Command(c_command, name=name))
    s_command = (nextcord.slash_command(name=name,
                                        description=f"executes a {name} action towards selected user, if allowed")
                 (s_command))

    # inject command into class by putting it into a variable in it's frame
    inspect.currentframe().f_back.f_locals[f"_command_c{name}"] = c_command
    inspect.currentframe().f_back.f_locals[f"_command_s{name}"] = s_command


def user_accepts(member, *actions):
    if isinstance(member, nextcord.User) or member.discriminator == "0000":
        return True

    for action in actions:
        role = nextcord.utils.get(member.roles, name=f"no {action}")

        allowed = role is None

        if not allowed:
            return False
    return True
