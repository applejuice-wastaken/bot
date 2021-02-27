from __future__ import annotations

import traceback
from dataclasses import dataclass
from textwrap import indent
from typing import List

# this stores the str output instead of the actual frames
# because of space and such
# and also because it doesn't make sense to store a large amount
# of stuff to then just display it at a smaller resolution

@dataclass
class FrameVariablesPair:
    frame_line: str
    variables_output: str

@dataclass
class FrozenTracebackException:
    frames_output: List[FrameVariablesPair]
    full_stack_trace: str
    discord_stack_trace: str

    cause: FrozenTracebackException = None
    context: FrozenTracebackException = None

    def get_full_console_output(self, chain=True):
        build = ""
        if chain:
            if self.cause is not None:
                build += self.cause.get_full_console_output()
                build += traceback._cause_message

            if self.context is not None:
                build += self.context.get_full_console_output()
                build += traceback._context_message

        build += f"{self.full_stack_trace}Locals:\n" \
                 f"{indent(self.frames_output[-1].variables_output, '    ')}"

        return build
