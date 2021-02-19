from abc import ABC, abstractmethod
from typing import Collection


class Category:
    def __init__(self, content):
        self.content = content


class Verb(Category):
    pass


class Literal(Category):
    pass


class RoundAction(ABC):
    def __init__(self, player):
        self.player = player

    @abstractmethod
    def represent(self, is_first_person) -> Collection[Category]:
        pass

    def get_author(self):
        return self.player
