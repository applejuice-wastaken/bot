from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Union, Tuple, Optional

from reactive_message.ReactiveMessage import ReactiveMessage
from reactive_message.RenderingProperty import RenderingProperty


def chain(func):
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        return self
    return wrapper

class _PageLocker:
    def __init__(self, page, reactive_message, args):
        self.args = args
        self.reactive_message = reactive_message
        self.page = page

    async def __aenter__(self):
        await self.page.lock.acquire()
        self.page.current_message = self.reactive_message
        self.page.current_args = self.args

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.page.current_message = None
        self.page.current_args = None
        self.page.lock.release()

class Ctx:
    def __init__(self, page):
        self._parent = page

    def __getattr__(self, item):
        return getattr(self._parent.current_message, item)

    def __setattr__(self, key, value):
        if key == "_parent":
            super(Ctx, self).__setattr__(key, value)
        else:
            setattr(self._parent.current_message, key, value)

    def __delattr__(self, item):
        delattr(self._parent.current_message, item)

    def __getitem__(self, item):
        return self._parent.current_args[item]

class Page(ABC):
    def __init__(self):
        self.current_message: Optional[RoutedReactiveMessage] = None
        self.current_args: Optional[Dict[str, str]] = None
        self.ctx = Ctx(self)
        self.lock = asyncio.Lock()

    def with_context(self, obj, args):
        return _PageLocker(self, obj, args)

    @abstractmethod
    def render_message(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def on_reaction_add(self, reaction, user):
        pass

    async def on_message(self, message):
        pass


class Route:
    def __init__(self):
        self.routes = {}
        self.fallback_var = None
        self.fallback = None
        self.vararg = None
        self.vararg_var = None
        self.base_page = None

    @chain
    def add_route(self, route_name, route: Union[Route, Page]):
        self.routes[route_name] = route

    @chain
    def add_fallback(self, var, route: Union[Route, Page]):
        self.fallback_var = var
        self.fallback = route

    def add_vararg(self, var, route: Page):
        self.vararg = route
        self.vararg_var = var

    @chain
    def base(self, page: Page):
        self.base_page = page


class RoutedReactiveMessage(ReactiveMessage):
    ROUTE = None
    ERROR_PAGE = None
    route = RenderingProperty("route")

    def __init__(self, cog, channel):
        super().__init__(cog, channel)

        if type(self).ROUTE is None:
            raise RuntimeError("Route is unfilled")

        self.route = ""
        self._cache_page = None
        self._cache_args = None

    def get_page(self) -> Tuple[Page, dict]:
        particles = self.route.split(".")
        current = self.ROUTE
        args = {}

        for idx, particle in enumerate(particles):
            if particle == "":
                continue

            if isinstance(current, Route):
                for route_name, route in current.routes.items():
                    if particle == route_name:
                        current = route
                        break

                else:
                    if current.fallback_var is not None:
                        args[current.fallback_var] = particle
                        current = current.fallback
                        continue

                    if current.vararg is not None:
                        args[current.vararg_var] = ".".join(particles[idx:])
                        current = current.vararg
                        break

        if isinstance(current, Route):
            if current.base_page is None:
                if self.ERROR_PAGE is None:
                    raise RuntimeError("Route is invalid")
                else:
                    current = self.ERROR_PAGE

            else:
                current = current.base_page

        return current, args

    async def render_message(self) -> Dict[str, Any]:
        self._cache_page, self._cache_args = self.get_page()
        async with self._cache_page.with_context(self, self._cache_args):
            return self._cache_page.render_message()

    async def on_message(self, message):
        await super(RoutedReactiveMessage, self).on_message(message)
        async with self._cache_page.with_context(self, self._cache_args):
            return await self._cache_page.on_message(message)

    async def on_reaction_add(self, reaction, user):
        await super(RoutedReactiveMessage, self).on_reaction_add(reaction, user)
        async with self._cache_page.with_context(self, self._cache_args):
            return await self._cache_page.on_reaction_add(reaction, user)
