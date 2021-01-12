from abc import ABC, abstractmethod


class RoundAction(ABC):
    def __init__(self, player):
        self.player = player

    @abstractmethod
    def represent(self, is_first_person) -> str:
        pass
