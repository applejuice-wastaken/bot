from __future__ import annotations

import asyncio
import typing
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

process_pool = ThreadPoolExecutor(2)


def execute(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(process_pool, partial(func, *args, **kwargs))
