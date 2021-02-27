from typing import Dict, Any

import discord

from cogs.command_error.capture import FrozenTracebackException
from reactive_message.ReactiveMessage import ReactiveMessage
from reactive_message.RenderingProperty import RenderingProperty


class TracebackExceptionAnalyzer(ReactiveMessage):
    GO_TO_START = "\u23ee\ufe0f"
    NEXT = "\u2b07\ufe0f"
    BACK = "\u2b06\ufe0f"
    CAUSE = "\U0001f1e6"
    CONTEXT = "\U0001f1e8"

    original = RenderingProperty("original")
    current = RenderingProperty("current")
    frame_index = RenderingProperty("frame_index")

    def __init__(self, bot, channel, frozen_exception: FrozenTracebackException):
        super().__init__(bot, channel)
        self.original = frozen_exception
        self.current = frozen_exception
        self.frame_index = 0

    def render_message(self) -> Dict[str, Any]:
        embed = discord.Embed(title="Exception")

        embed.add_field(name="traceback", value=self.current.discord_stack_trace, inline=False)
        embed.add_field(name="Current Frame line",
                        value=f"```py\n{self.current.frames_output[self.frame_index].frame_line}```")

        embed.add_field(name="Current Frame locals",
                        value=f"```\n{self.current.frames_output[self.frame_index].variables_output}```", inline=False)

        reactions = []

        if self.original is not self.current:
            reactions.append(self.GO_TO_START)

        reactions.append(self.NEXT)
        reactions.append(self.BACK)

        if self.current.cause is not None:
            reactions.append(self.CAUSE)

        if self.current.context is not None:
            reactions.append(self.CONTEXT)

        return dict(embed=embed, reactions=reactions)

    async def process_reaction_add(self, reaction, user):
        if reaction.emoji == self.NEXT:
            self.frame_index += 1

        elif reaction.emoji == self.BACK:
            self.frame_index -= 1

        elif reaction.emoji == self.CAUSE:
            self.frame_index = 0
            self.current = self.current.cause

        elif reaction.emoji == self.CONTEXT:
            self.frame_index = 0
            self.current = self.current.context

        elif reaction.emoji == self.GO_TO_START:
            self.frame_index = 0
            self.current = self.original
