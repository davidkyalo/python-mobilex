import asyncio
import dataclasses
import logging
import time
import typing as t
from collections import abc
from hashlib import md5

from mobilex.utils import to_bytes
from mobilex.utils.types import NamespaceDict

if t.TYPE_CHECKING:
    from mobilex.cache.base import BaseCache

    from . import Request, Response
    from .screens import ScreenState

logger = logging.getLogger(__package__)

_T = t.TypeVar("_T", covariant=True)

_object_new = object.__new__


@dataclasses.dataclass()
class SessionKey:
    __slots__ = (
        "msisdn",
        "ident",
    )  #'timestamp',

    msisdn: str
    ident: str

    def __str__(self):
        return f"{self.msisdn}/{self.ident}"


class Session:
    restored = None
    _is_started = False

    @t.overload
    def __init__(self, ttl: int, key: SessionKey):
        ...

    @t.overload
    def __init__(self, ttl: int, msisdn: str, id: t.Optional[str] = None):
        ...

    def __init__(self, ttl: int, key: SessionKey, id: t.Optional[str] = None):
        isinstance(key, SessionKey) or (key := SessionKey(key, id or None))
        self.key, self.ttl, self.created_at, self.accessed_at = key, ttl, None, None
        self.data, self.argv, self.restored = NamespaceDict(), None, None

    @property
    def pk(self):
        return self.key.msisdn

    @property
    def msisdn(self):
        return self.key.msisdn

    @property
    def id(self):
        return self.key.ident

    @property
    def age(self) -> float:
        return 0 if self.is_new else time.time() - self.accessed_at

    @property
    def is_stale(self) -> bool:
        return self.age >= self.ttl

    @property
    def is_new(self) -> bool:
        return self.accessed_at == self.created_at

    @property
    def state(self) -> "ScreenState":
        return self.data.get("__state__")

    @state.setter
    def state(self, value):
        self.data["__state__"] = value

    def start_request(self, request: "Request") -> t.NoReturn:
        assert not self._is_started
        session_id = request.session_id
        if int(self.id is None) + int(session_id is None) == 1:
            self.reset()
        elif session_id != self.id or (self.id is None and self.is_stale):
            self.restored = self.key
            self.key = SessionKey(self.msisdn, session_id)
            self.accessed_at = min(self.accessed_at, time.time() - self.ttl - 1)
        elif self.restored is None:
            self.accessed_at = time.time()
            self.created_at = self.created_at or self.accessed_at
        self._is_started = True

    def finalize(self, request: "Request") -> t.NoReturn:
        assert self._is_started
        del self._is_started
        self.accessed_at = time.time()

    def reset(self):
        self.data.clear()
        self.reset_restored()
        self.created_at = self.accessed_at = time.time()

    def reset_restored(self):
        self.restored = None

    def __contains__(self, key):
        return key in self.data

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def pop(self, key, *default):
        return self.data.pop(key, *default)

    def setdefault(self, key, value):
        return self.data.setdefault(key, value)

    def update(self, *arg, **kw):
        self.data.update(*arg, **kw)

    def __eq__(self, other):
        return isinstance(other, Session) and self.key == other.key

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.key)

    def __str__(self):
        return f'{self.__class__.__name__}("{self.key}")'


class NavId(t.NamedTuple):
    """Unique"""

    path: bytes
    name: bytes

    def digest(self):
        return md5(bytes(self)).digest()

    def __bool__(self):
        return any(self)

    def __bytes__(self):
        return b"|".join(v for v in self if v)

    def __truediv__(self, seg: bytes):
        if isinstance(seg, bytes):
            return self.__class__(self.digest() if self else None, seg)
        return NotImplemented


class History:
    __slots__ = "stack", "key_prefix", "backend", "background", "__weakref__"

    stack: list[NavId]
    backend: "BaseCache"
    background: list[abc.Awaitable]

    def __new__(cls, request: "Request", session: "Session"):
        app, self = request.app, _object_new(cls)
        self.backend, self.background = app.history_backend, []
        self.stack = session.setdefault("__state_stack", [NavId(None, None)])
        self.key_prefix = to_bytes(buri) + b"|" if (buri := request.base_uri) else b""
        return self

    async def finalize(self):
        background = self.background
        del self.stack, self.background
        background and await asyncio.gather(*background)

    def __len__(self):
        return len(self.stack)

    async def pop(self, k: int = None):
        # k is None and (k := -1)
        k = -1 if k is None else k + 1 if k > -1 else k
        stack = self.stack
        stack[k:] = []
        if id := stack[-1]:
            return await self.backend.get(self.make_key(id))

    async def push(self, res: "Response"):
        screen = to_bytes(res.to)
        head = self.stack[-1]
        if head.name != screen:
            self.stack.append(id := head / screen)
            coro = self.backend.set(self.make_key(id), res)
            self.background.append(asyncio.ensure_future(coro))

    def make_key(self, id: NavId):
        return self.key_prefix + id.digest()


class SessionManager:
    def create(self, req: "Request") -> Session:
        con = req.app.config
        return con.session_class(con.session_ttl, req.msisdn, req.session_id)

    async def load(self, req: "Request") -> Session:
        return await req.app.session_backend.get(self.make_key(req))

    async def persist(self, req: "Request", session) -> None:
        return await req.app.session_backend.set(self.make_key(req), session)

    async def open(self, request: "Request"):
        session = await self.load(request) or self.create(request)
        if isinstance(rv := session.start_request(request), abc.Awaitable):
            await rv
        request.session = session
        request.history = History(request, session)
        return request

    async def close(self, request: "Request", response):
        session, history = request.session, request.history
        tasks = (
            history.finalize(),
            session.finalize(request),
            self.persist(request, session),
        )
        await asyncio.gather(*(x for x in tasks if isinstance(x, abc.Awaitable)))

    def make_key(self, req: "Request"):
        return f"{req.base_uri}|{req.msisdn}"
