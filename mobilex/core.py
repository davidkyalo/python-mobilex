import typing as t
from collections import abc
from datetime import timedelta
from functools import cached_property

from mobilex.utils.types import FrozenNamespaceDict

from .router import Router
from .sessions import History, Session, SessionManager
from .utils import ArgumentVector, to_timedelta

if t.TYPE_CHECKING:
    from .cache.base import BaseCache
    from .response import Response


class ConfigDict(t.TypedDict, total=False):
    max_page_length: int
    session_class: type[Session]
    session_key_prefix: str
    session_backend: type["BaseCache"]
    session_manager: SessionManager | abc.Callable[..., SessionManager]
    session_ttl: float | timedelta

    history_class: type[History]
    history_backend: type["BaseCache"]
    history_key_prefix: type["BaseCache"]
    history_ttl: float | timedelta


class AppConfig(FrozenNamespaceDict):
    __slots__ = ()

    max_page_length: int

    session_class: type[Session]
    session_key_prefix: str
    session_backend: type["BaseCache"]
    session_manager: SessionManager | abc.Callable[..., SessionManager]
    session_ttl: float | timedelta

    history_class: type[History]
    history_backend: type["BaseCache"]
    history_key_prefix: type["BaseCache"]
    history_ttl: float | timedelta


class Request:
    args: ArgumentVector
    app: "App"
    session: "Session"
    history: "History"

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

    @cached_property
    def base_uri(self):
        return "*".join(filter(None, (self.service_code, self.initial_code)))


class App:
    router: Router
    session_manager: "SessionManager"
    name: t.Final[str]
    _initial_config: dict[str, t.Any]

    def __init__(self, name: str = None, **config):
        self.name = "mobilex.app" if name is None else name
        self.has_booted = False
        self._initial_config = self.get_default_config().copy()
        config and self.configure(config)

    @cached_property
    def config(self):
        conf = self._initial_config
        del self._initial_config
        return AppConfig(conf)

    @cached_property
    def session_manager(self):
        cb = self.config.session_manager
        return cb() if callable(cb) else cb

    @cached_property
    def session_backend(self):
        conf = self.config
        return conf.session_backend(
            self, ttl=conf.session_ttl, key_prefix=conf.session_key_prefix
        )

    @cached_property
    def history_backend(self):
        conf = self.config
        cls = conf.history_backend or conf.session_backend

        return cls(
            self,
            ttl=conf.history_ttl
            or min(map(to_timedelta, (conf.session_ttl * 10, 3 * 3600))),
            key_prefix=conf.history_key_prefix,
        )

    def configure(self, *args, **kwargs):
        if not hasattr(self, "_initial_config"):
            raise RuntimeError(
                f"App already initialized and can no longer be configured."
            )
        self._initial_config.update(*args, **kwargs)

    def get_default_config(self):
        from .cache.redis import RedisCache

        return ConfigDict(
            max_page_length=182,
            session_ttl=75,
            session_key_prefix="session",
            session_class=Session,
            session_backend=RedisCache,
            session_manager=SessionManager,
            history_key_prefix="state",
            history_backend=None,
            history_class=History,
            history_ttl=None,
        )

    def setup(self):
        assert (
            not self.has_booted
        ), f"{type(self).__name__}.boot() called multiple times."

        self.config
        self.router.run_embeded(self)
        self.has_booted = True
        return self

    def include_router(self, router, name: t.Optional[str] = None):
        self.router = router

    async def close_session(self, request: Request, response: "Response"):
        await self.session_manager.close(request, response)

    async def prepare_request(self, request: Request) -> Request:
        request.app = self
        await self.session_manager.open(request)

    async def teardown_request(self, request, response):
        await self.close_session(request, response)

    async def adispatch(self, request, *args, **kwargs):
        await self.prepare_request(request)
        response = await self.router(request)
        return await self.teardown_request(request, response) or response
