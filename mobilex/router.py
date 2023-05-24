import logging
import typing as t

from .const import ResponseType
from .exc import ScreenNotFoundError
from .responses import RedirectResponse, Response
from .screens import CON, END, Screen, ScreenState
from .utils import ArgumentVector

logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:
    from . import App, Request, Response


class Router:
    def __init__(self, name: str = None):
        self.name = name
        self._registry = {}
        self._entry_screen_name = self._home_screen_name = None

    # @property
    # def _home_screen_name(self):
    #     try:
    #         return self.__dict__["_home_screen_name"]
    #     except KeyError:
    #         return self._entry_screen_name

    # @_home_screen_name.setter
    # def _home_screen_name(self, value):
    #     self.__dict__["_home_screen_name"] = value

    def screen(
        self,
        name: str,
        screen: type[Screen] = None,
        *,
        entry: bool = None,
        home: bool = None,
    ):
        def decorator(scr):
            self._registry[name] = scr
            if home:
                self._home_screen_name = name
            if entry:
                self._entry_screen_name = name
            return scr

        return decorator if screen is None else decorator(screen)

    def entry_screen(self, name: str, screen: type[Screen] = None):
        return self.screen(name, screen, entry=True)

    def home_screen(self, name: str, screen: type[Screen] = None):
        return self.screen(name, screen, home=True)

    def get_screen(self, name: str):
        try:
            return self._registry[name]
        except KeyError:
            raise ScreenNotFoundError(name=name)

    def get_entry_screen(self, *, with_name=False):
        screen = self.get_screen(name := self._entry_screen_name)
        return (name, screen) if with_name else screen

    def get_home_screen(self, *, with_name=False):
        name = self._home_screen_name or self._entry_screen_name
        screen = self.get_screen(name)
        return (name, screen) if with_name else screen

    # def abs_screen_name(self, name: str):
    #     return name if name[:1] == "/" else f"/{self.name}/{name}"

    # def eval_argv(self, request: "Request") -> "Response":
    #     session = request.session
    #     argv = ArgumentVector(
    #         service_code=request.service_code,
    #         argstr=request.ussd_string,
    #         base_code=request.initial_code,
    #     )

    #     if session.is_stale or not (oldargv := session.argv):
    #         request.args = argv.args
    #     else:
    #         request.args = argv - oldargv

    #     session.argv = argv

    def create_new_state(self, name, screen: type[Screen]) -> "ScreenState":
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
            name, screen = self.get_entry_screen(with_name=True)
            session.state = state = self.create_new_state(name, screen)

        # if state is None:
        #     raise RuntimeError("Screen state cannot be None.")

        rv = await self.dispatch_to_screen(request, state, *request.args)
        return rv

    async def dispatch_to_screen(
        self, request: "Request", state: "ScreenState", inpt=None, /, *args
    ):
        screen = self.create_screen(state, request)

        try:
            res = await screen(request, inpt)
        except Exception as e:  # pragma: no cover
            logger.exception(e)
            raise e

        if isinstance(res, RedirectResponse):
            if res.type == ResponseType.POP:
                if not (ores := await request.history.pop(res.to)):
                    state = request.session.state = self.create_new_state(
                        *self.get_home_screen(with_name=True)
                    )
                    state.update(res.ctx)
                else:
                    state = request.session.state = self.create_new_state(
                        ores.to, self.get_screen(ores.to)
                    )
                    state.update(ores.ctx), state.update(res.ctx)
                return await self.dispatch_to_screen(request, state, *args)
            else:
                state = request.session.state = self.create_new_state(
                    res.to, self.get_screen(res.to)
                )
                state.update(res.ctx)

                await request.history.push(res)
                res.content is None or (args := (res.content,) + args)
                return await self.dispatch_to_screen(request, state, *args)

        request.session.state = screen.state
        assert isinstance(
            res, (str, Response)
        ), "Screen must return Response object or string."
        return str(res)

    async def __call__(self, request):
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

        return await self.dispatch_request(request)
