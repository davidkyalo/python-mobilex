from collections import ChainMap
from datetime import timedelta
from functools import cached_property
import typing as t

from mobilex.utils.types import FrozenNamespaceDict, ReadonlyDict

from .router import UssdRouter
from .utils import ArgumentVector


if t.TYPE_CHECKING:
    from .sessions import Session, SessionManager


class ConfigDict(t.TypedDict, total=False):
    session_key_prefix: str
    session_timeout: int | float | timedelta
    screen_state_timeout: int | float | timedelta
    max_page_length: int


class AppConfig(FrozenNamespaceDict):
    __slots__ = ()

    session_key_prefix: str
    session_timeout: int | float | timedelta
    screen_state_timeout: int | float | timedelta
    max_page_length: int


class Request:
    args: ArgumentVector
    app: "App"
    session: "Session"

    msisdn: str
    session_id: t.Union[str, int] = None

    service_code: str = None
    initial_code: str = None
    ussd_string: str = ""

    def __init__(
        self,
        msisdn: str,
        *,
        ussd_string: str = "",
        session_id: str = None,
        service_code: str = None,
        initial_code: str = None,
    ):
        self.msisdn = msisdn
        self.session_id = session_id
        self.ussd_string = ussd_string
        self.service_code = service_code
        self.initial_code = initial_code


class Response(object):
    ...


class App:
    router: UssdRouter
    session_manager: "SessionManager"

    default_config: t.ClassVar[ConfigDict] = ReadonlyDict(
        ConfigDict(
            session_timeout=75,
            session_key_prefix="mobilex.app.session",
            screen_state_timeout=120,
            max_page_length=182,
        )
    )
    _initial_config: dict[str, t.Any]

    def __init__(self, *, session_manager: "SessionManager", config: ConfigDict = None):
        self.has_booted = False
        self._initial_config = {**self.default_config}
        self.session_manager = session_manager
        if not config is None:
            self.configure(config)

    @cached_property
    def config(self):
        conf = self._initial_config
        del self._initial_config
        return AppConfig(conf)

    def configure(self, *args, **kwargs):
        if not hasattr(self, "_initial_config"):
            raise RuntimeError(
                f"App already initialized and can no longer be configured."
            )
        self._initial_config.update(*args, **kwargs)

    async def run(self):
        assert (
            not self.has_booted
        ), f"{self.__class__.__name__}.boot() called multiple times."

        sm = self.session_manager
        await sm.setup(self)
        self.router.run_embeded(self)

        self.config
        self.has_booted = True
        return self

    def include_router(self, router, name: t.Optional[str] = None):
        self.router = router

    async def open_session(self, request: Request):
        await self.session_manager.open_session(request)

    async def close_session(self, request: Request, response: Response):
        await self.session_manager.close_session(request, response)

    async def prepare_request(self, request: Request) -> Request:
        request.app = self
        await self.open_session(request)

    async def teardown_request(self, request, response):
        await self.close_session(request, response)

    async def __call__(self, request, *args, **kwargs):
        request = await self.prepare_request(request) or request
        response = await self.router(request)
        return await self.teardown_request(request, response) or response
