import random
from enum import Enum

import nextcord

from games.round.RoundGame import Direction


class CardType:
    @classmethod
    def other_place_attempt(cls, this, other, game):
        return this.color == other.color or \
               (this.number == other.number and other.number is not None and
                not issubclass(other.cls, AdversaryPayCardType)) or other.color is None

    @classmethod
    def get_user_friendly(cls, this):
        return f"{this.number} {color_to_emoji[this.color]}"

    @classmethod
    async def place(cls, this, game, attributes):
        return True

    @classmethod
    async def force_place(cls, this, game):
        await cls.place(this, game, {})

    @classmethod
    def required_attributes(cls, this):
        return {}


class ChangeColorOnPlaceCardType(CardType):
    @classmethod
    async def place(cls, this, game, attributes):
        this.color = attributes["color"]
        return True

    @classmethod
    async def force_place(cls, this, game):
        this.color = Color.YELLOW

    @classmethod
    def get_user_friendly(cls, this):
        if this.color is None:
            return f"{this.number if this.number is not None else 'Color change'} ⬛"
        else:
            return f"{this.number if this.number is not None else 'Color change'} {color_to_emoji[this.color]}"

    @classmethod
    def required_attributes(cls, this):
        return {"color": Color}


class ReverseDirection(CardType):
    @classmethod
    async def place(cls, this, game, attributes):
        if game.direction == Direction.UP_WARDS:
            game.direction = Direction.DOWN_WARDS
        else:
            game.direction = Direction.UP_WARDS
        return True

    @classmethod
    def other_place_attempt(cls, this, other, game):
        return other.cls is ReverseDirection or CardType.other_place_attempt(this, other, game)

    @classmethod
    def get_user_friendly(cls, this):
        return f"Reverse Card {color_to_emoji[this.color]}"


class BlockPersonCardType(CardType):
    @classmethod
    async def place(cls, this, game, attributes):
        game.cycle()

    @classmethod
    def other_place_attempt(cls, this, other, game):
        return other.cls is BlockPersonCardType or CardType.other_place_attempt(this, other, game)

    @classmethod
    def get_user_friendly(cls, this):
        return f"Block Card {color_to_emoji[this.color]}"


class AdversaryPayCardType(CardType):
    @classmethod
    def other_place_attempt(cls, this, other, game):
        if game.cards_to_take > 0:
            return issubclass(other.cls, AdversaryPayCardType)
        else:
            return issubclass(other.cls, AdversaryPayCardType) or CardType.other_place_attempt(this, other, game)

    @classmethod
    async def place(cls, this, game, attributes):
        game.cards_to_take += this.number

    @classmethod
    async def force_place(cls, this, game):
        await AdversaryPayCardType.place(this, game, {})

    @classmethod
    def get_user_friendly(cls, this):
        return f"+{this.number} {color_to_emoji[this.color]}"


class AdversaryPayColorOnPlaceCardType(AdversaryPayCardType, ChangeColorOnPlaceCardType):
    @classmethod
    def get_user_friendly(cls, this):
        if this.color is None:
            return f"+{this.number} ⬛"
        else:
            return f"+{this.number} {color_to_emoji[this.color]}"

    @classmethod
    async def place(cls, this, game, attributes):
        await AdversaryPayCardType.place(this, game, attributes)
        await ChangeColorOnPlaceCardType.place(this, game, attributes)

    @classmethod
    async def force_place(cls, this, game):
        await AdversaryPayCardType.force_place(this, game)
        await ChangeColorOnPlaceCardType.force_place(this, game)

    @classmethod
    def other_place_attempt(cls, this, other, game):
        return AdversaryPayCardType.other_place_attempt(this, other, game)


class Color(Enum):
    @classmethod
    async def on_message(cls, game, message):
        pass

    @classmethod
    async def on_reaction_add(cls, game, reaction, user):
        if reaction.message.id == game.bound_message.id and \
                user.id == game.current_player.id:
            await cls.finish(game, emoji_to_color[reaction.emoji])

    @classmethod
    async def begin(cls, game):
        embed = nextcord.Embed(title="Pick a color", description="", color=0x00ff00)

        game.bound_message = await game.current_player.send(embed=embed)

        for emoji in emoji_to_color:
            await game.bound_message.add_reaction(emoji)

    @classmethod
    async def finish(cls, game, value):
        game.round_timeout += 5
        game.attributes[game.filling_attribute] = value
        await game.next_attribute_filling()

    RED = 1
    YELLOW = 2
    GREEN = 3
    BLUE = 4


color_to_emoji = {
    Color.GREEN: "🟩",
    Color.YELLOW: "🟨",
    Color.RED: "🟥",
    Color.BLUE: "🟦"
}

emoji_to_color = {
    "🟩": Color.GREEN,
    "🟨": Color.YELLOW,
    "🟥": Color.RED,
    "🟦": Color.BLUE
}


class CardInstance:
    def __init__(self, cls, color, number):
        self.number = number
        self.color = color
        self.cls = cls

    def __getattr__(self, item):
        def _(*args, **kwargs):
            return getattr(self.cls, item)(self, *args, **kwargs)

        return _


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
