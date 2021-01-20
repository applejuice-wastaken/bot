import itertools
from collections import namedtuple
from enum import Enum
import random

class CardNumber(Enum):
    A = 1
    N2 = 2
    N3 = 3
    N4 = 4
    N5 = 5
    N6 = 6
    N7 = 7
    N8 = 8
    N9 = 9
    N10 = 10
    J = 11
    Q = 12
    K = 13

class CardType(Enum):
    hearts = 0
    diamonds = 1
    clubs = 2
    spades = 3

class Card(namedtuple("CardTuple", "number type")):
    def __str__(self):
        type_ = "♥♦♣♠"[self.type.value]

        if self.number in (CardNumber.A, CardNumber.J, CardNumber.K, CardNumber.Q):
            number = self.number.name
        else:
            number = str(self.number.value)

        return f"{number} {type_}"

def generate_deck():
    ret = [Card(CardNumber(val[0]), CardType(val[1])) for val in itertools.product(range(1, 14), range(4))]
    random.shuffle(ret)
    return ret
