import datetime
import time

import expression
import humanize
from discord.ext import commands

class ExpressionParser:
    @staticmethod
    async def evaluate_expression(content, user, emoji, message):
        times_reacted = 0
        global_reactions = 0
        reaction_count = 0

        for reaction in message.reactions:
            async for other_member in reaction.users():
                if user.id == other_member.id:
                    times_reacted += 1

            if emoji == reaction.emoji:
                reaction_count = reaction.count

            global_reactions += reaction.count

        parser = expression.Expression_Parser(
            {
                "member_id": user.id,
                "member_nick": str(user),
                "reaction": emoji,
                "times_reacted": times_reacted,
                "global_reactions": global_reactions,
                "reaction_count": reaction_count
            }
        )

        return_val = parser.parse(content)

        return return_val

    @staticmethod
    def validate_remove(content, user, emoji, message):
        return ExpressionParser.evaluate_expression(content, user, emoji, message)

class InvertedExperssionParser(ExpressionParser):
    @staticmethod
    async def validate_remove(content, user, emoji, message):
        return not await ExpressionParser.evaluate_expression(content, user, emoji, message)


main_chunk_names = {"if": ExpressionParser, "unless": InvertedExperssionParser}
restrictions = []

class Restriction:
    def __init__(self, message_id, expires, chunks):
        self.chunks = chunks
        self.expires = expires
        self.message_id = message_id

    async def test_for(self, user, emoji, message):
        for chunk in self.chunks:
            classed_chunk = main_chunk_names[chunk.name]
            remove_it = await classed_chunk.validate_remove(chunk.content, user, emoji, message)

            if remove_it:
                return True
        return False


class Chunk:
    def __init__(self, name, content):
        self.content = content
        self.name = name

    def __repr__(self):
        return f"<content={repr(self.content)} name={repr(self.name)}>"

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_state = {}
        self.game_instances = []
        self.play_list = {}

    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.command()
    async def restrict_reactions(self, ctx, message: int, expire: int, *, tokens):
        pointer = 0

        initial_chunks = []

        while pointer < len(tokens):
            for chunk_name in main_chunk_names:
                if chunk_name + " " == tokens[pointer:pointer + len(chunk_name) + 1]:
                    if len(initial_chunks) > 0:
                        initial_chunks[-1].content = initial_chunks[-1].content[:-1]
                    initial_chunks.append(Chunk(chunk_name, ""))
                    pointer += len(chunk_name) + 1
                    break
            else:
                initial_chunks[-1].content += tokens[pointer]
                pointer += 1

        restrictions.append(Restriction(message, time.time() + expire, initial_chunks))

        await ctx.send(f"New restriction is going to be applied for approximately "
                       f"{humanize.naturaldelta(datetime.timedelta(seconds=expire))}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.event_type == "REACTION_ADD":
            to_remove = []

            for idx, restriction in enumerate(restrictions):
                print(restriction.message_id, payload.message_id)
                if time.time() < restriction.expires and payload.message_id == restriction.message_id:
                    guild = self.bot.get_guild(payload.guild_id)
                    member = guild.get_member(payload.user_id)
                    channel = self.bot.get_channel(payload.channel_id)
                    message = await channel.fetch_message(payload.message_id)

                    remove = await restriction.test_for(member, payload.emoji, message)

                    if remove:
                        await message.remove_reaction(payload.emoji, member)

                if time.time() >= restriction.expires:
                    to_remove.append(idx)

            to_remove.reverse()

            for idx in to_remove:
                restrictions.pop(idx)

def setup(bot):
    bot.add_cog(Moderation(bot))
