from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Union, Tuple

from reactive_message.ReactiveMessage import ReactiveMessage
from reactive_message.RenderingProperty import RenderingProperty


def chain(func):
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        return self
    return wrapper

class Page(ABC):
    @abstractmethod
    def render_message(self, reactive_message, args: dict) -> Dict[str, Any]:
        raise NotImplementedError

    async def on_reaction_add(self, reaction, user, reactive_message, args: dict):
        pass

    async def on_message(self, message, reactive_message, args: dict):
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

    def render_message(self) -> Dict[str, Any]:
        self._cache_page, self._cache_args = self.get_page()
        return self._cache_page.render_message(self, self._cache_args)

    async def on_message(self, message):
        await super(RoutedReactiveMessage, self).on_message(message)
        return await self._cache_page.on_message(message, self, self._cache_args)

    async def on_reaction_add(self, reaction, user):
        await super(RoutedReactiveMessage, self).on_reaction_add(reaction, user)
        return await self._cache_page.on_reaction_add(reaction, user, self, self._cache_args)
