import asyncio
import random
from collections import namedtuple
from enum import Enum
import utils


class CardType:
    @staticmethod
    async def other_place_attempt(this, other, game):
        return this.color == other.color or \
               (this.number == other.number and other.number is not None) or other.color is None

    @staticmethod
    def get_user_friendly(this):
        emojis = {
            Color.GREEN: "🟩",
            Color.YELLOW: "🟨",
            Color.RED: "🟥",
            Color.BLUE: "🟦"
        }

        return f"{this.number} {emojis[this.color]}"

    @staticmethod
    async def place(this, game):
        return True

    @staticmethod
    async def force_place(this, game):
        return True


class ChangeColorOnPlaceCardType(CardType):
    @staticmethod
    async def place(this, game):
        emojis = {
            "🟩": Color.GREEN,
            "🟨": Color.YELLOW,
            "🟥": Color.RED,
            "🟦": Color.BLUE
        }

        try:
            reaction, _, time_taken = await utils.choice(game.bot, game.current_player, "Which Color?",
                                                         "What color will be your card?", game.timeout, *emojis.keys())
        except asyncio.TimeoutError:
            this.color = Color.YELLOW
        else:
            game.timeout -= time_taken

            this.color = emojis[str(reaction)]

        return True

    @staticmethod
    async def force_place(this, game):
        this.color = Color.YELLOW

    @staticmethod
    def get_user_friendly(this):
        emojis = {
            Color.GREEN: "🟩",
            Color.YELLOW: "🟨",
            Color.RED: "🟥",
            Color.BLUE: "🟦"
        }

        if this.color is None:
            return f"{this.number if this.number is not None else 'Color change'} ⬛"
        else:
            return f"{this.number if this.number is not None else 'Color change'} {emojis[this.color]}"

class ReverseDirection(CardType):
    @staticmethod
    async def place(this, game):
        if game.direction == Direction.UP_WARDS:
            game.direction = Direction.DOWN_WARDS
        else:
            game.direction = Direction.UP_WARDS
        return True

    @staticmethod
    async def other_place_attempt(this, other, game):
        return other.cls is ReverseDirection or await CardType.other_place_attempt(this, other, game)

    @staticmethod
    def get_user_friendly(this):
        emojis = {
            Color.GREEN: "🟩",
            Color.YELLOW: "🟨",
            Color.RED: "🟥",
            Color.BLUE: "🟦"
        }

        return f"Reverse Card {emojis[this.color]}"


class BlockPersonCardType(CardType):
    @staticmethod
    async def place(this, game):
        game.make_round()
        return True

    @staticmethod
    async def other_place_attempt(this, other, game):
        return other.cls is BlockPersonCardType or await CardType.other_place_attempt(this, other, game)

    @staticmethod
    def get_user_friendly(this):
        emojis = {
            Color.GREEN: "🟩",
            Color.YELLOW: "🟨",
            Color.RED: "🟥",
            Color.BLUE: "🟦"
        }

        return f"Block Card {emojis[this.color]}"

class AdversaryPayCardType(CardType):
    @staticmethod
    async def other_place_attempt(this, other, game):
        if game.cards_to_take > 0:
            return issubclass(other.cls, AdversaryPayCardType) and await CardType.other_place_attempt(this, other, game)
        else:
            return await CardType.other_place_attempt(this, other, game)

    @staticmethod
    async def place(this, game):
        game.cards_to_take += this.number

    @staticmethod
    async def force_place(this, game):
        await AdversaryPayCardType.place(this, game)

    @staticmethod
    def get_user_friendly(this):
        emojis = {
            Color.GREEN: "🟩",
            Color.YELLOW: "🟨",
            Color.RED: "🟥",
            Color.BLUE: "🟦"
        }

        return f"+{this.number} {emojis[this.color]}"

class AdversaryPayColorOnPlaceCardType(AdversaryPayCardType, ChangeColorOnPlaceCardType):
    @staticmethod
    def get_user_friendly(this):
        emojis = {
            Color.GREEN: "🟩",
            Color.YELLOW: "🟨",
            Color.RED: "🟥",
            Color.BLUE: "🟦"
        }

        if this.color is None:
            return f"+{this.number} ⬛"
        else:
            return f"+{this.number} {emojis[this.color]}"

    @staticmethod
    async def place(this, game):
        await AdversaryPayCardType.place(this, game)
        await ChangeColorOnPlaceCardType.place(this, game)

    @staticmethod
    async def force_place(this, game):
        await AdversaryPayCardType.force_place(this, game)
        await ChangeColorOnPlaceCardType.force_place(this, game)

    @staticmethod
    async def other_place_attempt(this, other, game):
        return await AdversaryPayCardType.other_place_attempt(this, other, game)

class Color(Enum):
    RED = 1
    YELLOW = 2
    GREEN = 3
    BLUE = 4

class Direction(Enum):
    UP_WARDS = 1
    DOWN_WARDS = 2


class CardInstance:
    def __init__(self, cls, color, number):
        self.number = number
        self.color = color
        self.cls = cls

def generate_deck():
    deck = []

    for c in range(1, 5):
        for i in range(1, 10):
            deck.append(CardInstance(CardType, Color(c), i))
            deck.append(CardInstance(CardType, Color(c), i))

        deck.append(CardInstance(CardType, Color(c), 0))

        deck.append(CardInstance(BlockPersonCardType, Color(c), None))
        deck.append(CardInstance(BlockPersonCardType, Color(c), None))

        deck.append(CardInstance(ReverseDirection, Color(c), None))
        deck.append(CardInstance(ReverseDirection, Color(c), None))

        deck.append(CardInstance(AdversaryPayCardType, Color(c), 2))
        deck.append(CardInstance(AdversaryPayCardType, Color(c), 2))

        deck.append(CardInstance(ChangeColorOnPlaceCardType, None, None))

        deck.append(CardInstance(AdversaryPayColorOnPlaceCardType, None, 4))

    random.shuffle(deck)
    return deck

def setup():
    return [CardType, ChangeColorOnPlaceCardType, BlockPersonCardType,
            AdversaryPayCardType, AdversaryPayColorOnPlaceCardType]