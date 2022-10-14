import asyncio
import typing as t

from datetime import timedelta
import redis.asyncio as redis

from .base import BaseCache, AnyKey, Timeout, Version



loop = asyncio.get_event_loop()


class RedisCache(BaseCache):

	def __init__(self, **options):
		super().__init__(**options)
		self.store: redis.Redis = None

	async def setup(self, app=None):
		location = self.options.get('location') or 'redis://localhost'
		self.store =  redis.from_url(location)

	async def add(self, key, value, timeout=..., version=None) -> bool:
		"""
		Set a value in the cache if the key does not already exist. If
		timeout is given, use that timeout for the key; otherwise use the
		default cache timeout.

		Return True if the value was stored, False otherwise.
		"""
		timeout = self.get_timeout(timeout)
		if isinstance(timeout, float):
			return await self.store.set(
					self.make_key(key, version), 
					self.dumps(value), 
					pexpire=int(timeout * 1000), 
					exist=self.store.SET_IF_NOT_EXIST
				)
		else:
			return await self.store.set(
					self.make_key(key, version), 
					self.dumps(value), 
					expire=timeout, 
					exist=self.store.SET_IF_NOT_EXIST
				)

	async def get(self, key, version=None) -> t.Any:
		"""
		Fetch a given key from the cache. If the key does not exist, return
		default, which itself defaults to None.
		"""
		rv = await self.store.get(self.make_key(key, version))
		return rv if rv is None else self.loads(rv)

	async def set(self, key, value, timeout=..., version=None) -> bool:
		"""
		Set a value in the cache. If timeout is given, use that timeout for the
		key; otherwise use the default cache timeout.
		"""
		timeout = self.get_timeout(timeout)
		if isinstance(timeout, float):
			return await self.store.set(
					self.make_key(key, version), 
					self.dumps(value), 
					px=int(timeout * 1000), 
				)
		else:
			return await self.store.set(
					self.make_key(key, version), 
					self.dumps(value), 
					ex=timeout, 
				)

	async def delete(self, key, version=None) -> int:
		"""
		Delete a key from the cache, failing silently.
		"""
		return await self.store.delete(self.make_key(key, version))

	async def keys(self, pattern='*', version=None) -> int:
		"""
		Delete a key from the cache, failing silently.
		"""
		return await self.store.keys(self.make_key(pattern, version), encoding='utf-8')

	async def clear(self):
		"""Remove *all* values from the cache at once."""
		raise NotImplementedError('subclasses of BaseCache must provide a clear() method')

	async def close(self, **kwargs):
		"""Close the cache connection"""
		await self.store.close()
