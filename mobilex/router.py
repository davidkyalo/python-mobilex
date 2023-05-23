import logging
import typing as t

from .const import ResponseType
from .response import RedirectResponse, Response
from .screens import CON, END, Screen
from .utils import ArgumentVector

logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:
    from . import App, Request, Response


class Router:
    parent: "App"

    def __init__(self, name):
        self.name = name
        self._registry = {}
        self._start_screen = None

    @property
    def _home_screen(self):
        try:
            return self.__dict__["_home_screen"]
        except KeyError:
            return self._start_screen

    @_home_screen.setter
    def _home_screen(self, value):
        self.__dict__["_home_screen"] = value

    def run_embeded(self, parent):
        self.parent = parent

    def screen(self, name: str):
        def decorator(screen):
            nonlocal name, self
            self.register_screen(name, screen)
            return screen

        return decorator

    def register_screen(self, name: str, screen: t.Any):
        self._registry[name] = screen
        return screen

    def start_screen(self, name: str):
        def decorator(screen):
            nonlocal name, self
            self.register_start_screen(name, screen)
            return screen

        return decorator

    def register_start_screen(self, name: str, screen: t.Any):
        self._start_screen = name, screen
        return self.register_screen(name, screen)

    def home_screen(self, name: str):
        def decorator(screen):
            nonlocal name, self
            self.register_home_screen(name, screen)
            return screen

        return decorator

    def register_home_screen(self, name: str, screen: t.Any):
        self._home_screen = name, screen
        return self.register_screen(name, screen)

    def get_screen(self, name: str, default=...):
        nm, key = self.name, name
        if name.startswith(f"/{nm}/"):
            key = name[len(nm) + 2 :]

        if (rv := self._registry.get(key)) is not None:
            return rv
        elif default is ...:
            raise LookupError(f"UssdScreen {name!r} not found")
        return default

    def get_start_screen(self, *, withname=False):
        name, screen = self._start_screen
        return (f"/{self.name}/{name}", screen) if withname else screen

    def get_home_screen(self, *, withname=False):
        name, screen = self._home_screen
        return (f"/{self.name}/{name}", screen) if withname else screen

    def abs_screen_name(self, name: str):
        return name if name[:1] == "/" else f"/{self.name}/{name}"

    def eval_argv(self, request: "Request") -> "Response":
        session = request.session
        argv = ArgumentVector(
            service_code=request.service_code,
            argstr=request.ussd_string,
            base_code=request.initial_code,
        )

        if session.is_stale or not (oldargv := session.argv):
            request.args = argv.args
        else:
            request.args = argv - oldargv

        session.argv = argv

    def create_new_state(self, name, screen):
        cls = screen._state_class
        return cls(name)

    def create_screen(self, state, request: "Request") -> "Screen":
        cls = self.get_screen(state.screen)
        rv = cls(state)
        return rv

    async def dispatch_request(self, request: "Request"):
        session = request.session
        state = session.state

        if session.restored:
            screen = self.get_screen(state.screen)
            if request.args or not screen._meta.restore_sessions:
                session.reset()

        if session.is_new:
            name, screen = self.get_start_screen(withname=True)
            state = session.state = self.create_new_state(name, screen)
            inpt, args = None, request.args
        else:
            inpt, *args = request.args or (None,)

        if state is None:
            raise RuntimeError("Screen state cannot be None.")

        rv = await self.dispatch_to_screen(request, state, inpt, *args)
        return rv

    async def dispatch_to_screen(self, request: "Request", state, inpt=None, /, *args):
        screen = self.create_screen(state, request)

        try:
            if inpt is not None and not screen.state.get("__initialized__"):
                await screen(request)
            res = await screen(request, inpt)
        except Exception as e:
            logger.exception(e)
            raise e

        if isinstance(res, RedirectResponse):
            if res.type == ResponseType.POP:
                if res.to == 0 or not (ores := await request.history.pop(res.to)):
                    n, s = self.get_home_screen(withname=True)
                    state = request.session.state = self.create_new_state(n, s)
                    state.update(res.ctx)
                else:
                    n, s = ores.to, self.get_screen(ores.to)
                    state = request.session.state = self.create_new_state(n, s)
                    state.update(ores.ctx)
                    state.update(res.ctx)
                return await self.dispatch_to_screen(request, state, *args)
            else:
                n = res.to = self.abs_screen_name(res.to)
                s = self.get_screen(n)
                state = request.session.state = self.create_new_state(n, s)
                state.update(res.ctx)

                await request.history.push(res)
                res.content is None or (args := (res.content,) + args)
                return await self.dispatch_to_screen(request, state, *args)

        request.session.state = screen.state

        if res in (CON, END):
            return f"{res} {screen.payload}"
        elif isinstance(res, tuple):
            return " ".join(res)
        elif isinstance(res, str):
            return res
        raise RuntimeError("Screen must return Response object or string.")

    async def __call__(self, request, *args, **kwargs):
        self.eval_argv(request)
        return await self.dispatch_request(request)
