from __future__ import annotations

import re
import typing

from nextcord.ext.commands import MemberConverter, BadArgument

if typing.TYPE_CHECKING:
    pass


class TooManyExponents(BadArgument):
    def __init__(self, amount):
        self.amount = amount
        super().__init__('Too many exponents provided.')


class RelativeConversionNotFound(BadArgument):
    def __init__(self):
        super().__init__('Matching user was not found in last 20 messages.')


class TooManyMessageMentions(BadArgument):
    def __init__(self):
        super().__init__('Message has multiple mentions, ambiguity can occur.')


EXPONENTIAL_REGEX = re.compile(r"^(m?)(\^+)$")


class RelativeMemberConverter(MemberConverter):
    async def convert(self, ctx, argument):
        cache = getattr(ctx, "_cache_relative_member_converter", {})
        if argument in cache:
            return cache[argument]
        else:
            converted = await self.do_convert(ctx, argument)
            cache[argument] = converted
            ctx._cache_relative_member_converter = cache
            return converted

    async def do_convert(self, ctx, argument):
        if argument == "me":
            return ctx.author

        else:
            match = EXPONENTIAL_REGEX.match(argument)
            if match:
                many = len(match.group(2))
                flag = match.group(1)

                if many > 10:
                    raise TooManyExponents(many)

                last = ctx.author

                async for message in ctx.channel.history(before=ctx.message, limit=20):
                    if flag == "":
                        if message.author != last or \
                                (message.author.discriminator == "0000" and
                                 message.author.display_name != last.display_name):

                            last = message.author
                            many -= 1
                            if many == 0:
                                return await self.query_member_by_id(ctx.bot, ctx.guild, message.author.id) \
                                       or message.author

                    elif flag == "m":
                        if message.mentions:
                            many -= 1
                            if many == 0:
                                if len(message.mentions) == 1:
                                    return await self.query_member_by_id(ctx.bot, ctx.guild, message.mentions[0].id) \
                                           or message.author

                                raw_mentions = message.raw_mentions
                                if len(raw_mentions) == 1:
                                    return await self.query_member_by_id(ctx.bot, ctx.guild, raw_mentions[0]) \
                                           or message.author

                                raise TooManyMessageMentions
                else:
                    raise RelativeConversionNotFound

        return await super(RelativeMemberConverter, self).convert(ctx, argument)
