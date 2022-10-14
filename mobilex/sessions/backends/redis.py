import abc
import typing as t


from .base import SessionBackendABC, Key

Key = t.Union[str, t.Tuple[str]]


class RedisSessionBeckend(SessionBackendABC):
	
	def __init__(self, uri=''):
		pass

	@property
	def store(self):
		from django.core.cache import cache
		return cache

	async def get(self, key: Key) -> t.Any:
		key = self.make_key(*(key if isinstance(key, tuple) else (key,)))

	async def set(self, key: Key, value: t.Any, ttl: t.Optional[int] = None) -> int:
		raise NotImplementedError(f'{self.__class__.__module__}.{self.__class__.__name__}.set()')

	