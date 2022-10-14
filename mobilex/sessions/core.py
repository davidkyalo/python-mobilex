import time
import asyncio
import hashlib
import logging
import typing as t
import dataclasses
from collections import namedtuple

from mobilex.utils.uri import Uri
from mobilex.utils.types import AttributeMapping


if t.TYPE_CHECKING:
    from .managers import HistoryManager

logger = logging.getLogger(__package__)


@dataclasses.dataclass()
class SessionKey:

    __slots__ = 'msisdn', 'ident', #'timestamp',

    msisdn: str
    ident: str

    # timestamp: float = dataclasses.field(
    # 		init=False, compare=False, 
    # 		repr=False, default_factory=time.time
    # 	)

    # @property
    # def age(self) -> float:
    # 	return time.time() - self.timestamp
    
    def __str__(self):
        return f'{self.msisdn}/{self.ident}'


class Session:

    restored = None
    _is_started = False

    @t.overload
    def __init__(self, ttl: int, key: SessionKey): 
        ...
    @t.overload
    def __init__(self, ttl: int, msisdn: str, id: t.Optional[str]=None): 
        ...
    def __init__(self, ttl: int, key: SessionKey, id: t.Optional[str]=None):
        isinstance(key, SessionKey) or (key := SessionKey(key, id or None))		
        self.key = key
        self.ttl = ttl
        self.created_at = None
        self.accessed_at = None
        self.data = AttributeMapping()
        self.argv = None
        self.restored = None

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
    def state(self):
        return self.data.get('__state__')

    @state.setter
    def state(self, value):
        self.data['__state__'] = value
    
    async def start_request(self, request, *, session_id: t.Optional[str]=...) -> t.NoReturn:
        if self._is_started:
            return self
        
        session_id is ... and (session_id := request.session_id)

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

    async def finish_request(self, request) -> t.NoReturn:
        if self._is_started:
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

    # def __getstate__(self):
    # 	state = self.__dict__.copy()
    # 	# state.setdefault('restored', None)
    # 	return state

    def __eq__(self, other):
        return isinstance(other, Session) and self.key == other.key

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.key)

    def __str__(self):
        return f'{self.__class__.__name__}("{self.key}")'





class StateUri(Uri):
    """Unique 
    """
    __slots__ = ()

    @property
    def stem(self):
        return self[-1] if self else None

    @property
    def hash(self):
        return hashlib.md5(str(self).encode()).hexdigest()




class History:

    def __init__(self, manager: 'HistoryManager', stack: list=None):
        self.manager = manager
        self.stack = [] if stack is None else stack

    def __len__(self):
        return len(self.stack) + 1
    
    async def pop(self, k: int = None):
        k is None and (k := -1)
        stack = self.stack		
        stack[k:] = []
        if (path := stack and stack[-1] or None):
            return await self.manager.load_state(path.hash)

    async def push(self, res):
        screen = res.to
        prev = self.stack and self.stack[-1] or ''
        if not prev or prev.stem != screen:
            path = StateUri(prev, screen)
            self.stack.append(path)
            asyncio.create_task(self.manager.save_state(path.hash, res))



