from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Union, Tuple, Optional, Type

from reactive_message.ReactiveMessage import ReactiveMessage, checks_updates
from reactive_message.RenderingProperty import RenderingProperty


def chain(func):
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        return self
    return wrapper

class Page(ABC):
    def __init__(self, message, args: Dict[str, str]):
        self.message = message
        self.args = args

        self.lock = asyncio.Lock()

    @abstractmethod
    def render_message(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def process_reaction_add(self, reaction, user):
        pass

    async def process_message(self, message):
        pass

    async def on_leave(self):
        pass

    async def on_enter(self):
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
    def add_route(self, route_name, route: Union[Route, Type[Page]]):
        self.routes[route_name] = route

    @chain
    def add_fallback(self, var, route: Union[Route, Type[Page]]):
        self.fallback_var = var
        self.fallback = route

    def add_vararg(self, var, route: Type[Page]):
        self.vararg = route
        self.vararg_var = var

    @chain
    def base(self, page: Type[Page]):
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
        self._current_route = None
        self._current_page = None
        self._current_args = None

    def get_page(self) -> Tuple[Type[Page], dict]:
        if self.route == self._current_route:
            # route did not change
            return type(self._current_page), self._current_args

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

    async def change_page(self):
        route_page, route_args = self.get_page()

        if isinstance(self._current_page, route_page):
            self._current_page.args = route_args

        else:
            if self._current_page is not None:
                await self._current_page.on_leave()

            self._current_page = route_page(self, route_args)

            await self._current_page.on_enter()

        self._current_route = self.route
        self._current_args = route_args

    async def render_message(self) -> Dict[str, Any]:
        await self.change_page()

        return self._current_page.render_message()

    async def process_message(self, message):
        await super(RoutedReactiveMessage, self).process_message(message)

        return await self._current_page.process_message(message)

    async def process_reaction_add(self, reaction, user):
        await super(RoutedReactiveMessage, self).process_reaction_add(reaction, user)

        return await self._current_page.process_reaction_add(reaction, user)

    @checks_updates
    async def on_event(self, event_name, *args, **kwargs):
        method = f"on_{event_name}"
        if hasattr(self._current_page, method) and callable(getattr(self._current_page, method)):
            await getattr(self._current_page, method)(*args, **kwargs)
