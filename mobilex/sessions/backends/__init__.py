import abc
import typing as t



if t.TYPE_CHECKING:
    from mobilex import FlexUssd


Key = t.Union[str, t.Tuple[str]]


class SessionBackendABC(abc.ABC):
	
	key_sep: str = '|'

	def __init__(self, app: 'FlexUssd' = None):
		self.app = app

	@property
	def session_ttl(self) -> int:
		return self.app.config.SESSION_TIMEOUT

	@property
	def key_prefix(self) -> str:
		return self.app.config.SESSION_KEY_PREFIX

	@abc.abstractmethod
	async def get(self, key: Key) -> t.Any:
		raise NotImplementedError(f'{self.__class__.__module__}.{self.__class__.__name__}.get()')
	
	@abc.abstractmethod
	async def set(self, key: Key, value: t.Any, ttl: t.Optional[int] = None) -> int:
		raise NotImplementedError(f'{self.__class__.__module__}.{self.__class__.__name__}.set()')

	def make_key(self, *parts: str, prefix: Key = None) -> str:
		prefix = ':'.join(filter(None, (self.key_prefix,) + prefix)) \
				if isinstance(prefix, tuple) \
				else ':'.join(filter(None, (self.key_prefix, prefix,)))
		rv = self.key_sep.join(map(str, parts))
		return f'{prefix}{self.key_sep}{rv}' if prefix else rv



class RedisSessionBeckend(SessionBackendABC):
	
	def __init__(self, uri):
		pass

	@property
	def store(self):
		from django.core.cache import cache
		return cache

	async def get(self, key: Key) -> t.Any:
		key = self.make_key(*(key if isinstance(key, tuple) else (key,)))

	async def set(self, key: Key, value: t.Any, ttl: t.Optional[int] = None) -> int:
		raise NotImplementedError(f'{self.__class__.__module__}.{self.__class__.__name__}.set()')

	