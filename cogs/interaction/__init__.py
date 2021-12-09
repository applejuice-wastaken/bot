from __future__ import annotations

import typing

from cogs.interaction.interaction import Interaction

if typing.TYPE_CHECKING:
    pass


def setup(bot):
    bot.add_cog(Interaction(bot))
