import discord
import time


async def choice(bot, channel, title, message, timeout, *reactions):
    embed = discord.Embed(title=title, description=message, color=0x00ff00)

    message = await channel.send(embed=embed)

    for reaction in reactions:
        await message.add_reaction(reaction)

    def check(react, user):
        return user.id != bot.user.id and react.message.id == message.id and str(react.emoji) in reactions

    before_send = time.time()
    return *await bot.wait_for('reaction_add', timeout=timeout, check=check), time.time() - before_send
