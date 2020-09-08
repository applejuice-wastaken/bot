from abc import ABC, abstractmethod


class Game(ABC):
    def __init__(self, bot, guild, players):
        self.guild = guild
        self.players = players
        self.bot = bot

    @abstractmethod
    async def player_leave(self, player):
        self.players.remove(player)
        return True
