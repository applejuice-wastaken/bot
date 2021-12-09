from __future__ import annotations

import typing

from phrase_reference_builder.types import DeferredReference

if typing.TYPE_CHECKING:
    pass


author = DeferredReference("action_author")
valid = DeferredReference("valid")
rejected = DeferredReference("rejected")
condition = DeferredReference("condition")
