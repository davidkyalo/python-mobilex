import typing as t

import redis.asyncio as redis

from mobilex.utils import to_timedelta

from .base import BaseCache

if t.TYPE_CHECKING:
    from mobilex import App


class RedisCache(BaseCache):
    store: redis.Redis

    def __init__(self, app: "App", location=None, **options):
        super().__init__(app, **options)
        self.store = redis.from_url(location or "redis://localhost")

    async def get(self, key) -> t.Any:
        """
        Fetch a given key from the cache. If the key does not exist, return
        default, which itself defaults to None.
        """
        if (rv := await self.store.get(self.make_key(key))) is not None:
            rv = self.loads(rv)
        return rv

    async def set(self, key, value, ttl=None) -> bool:
        """
        Set a value in the cache. If timeout is given, use that timeout for the
        key; otherwise use the default cache timeout.
        """
        ttl = self.ttl if ttl is None else to_timedelta(ttl)
        return await self.store.set(self.make_key(key), self.dumps(value), px=ttl)

    async def delete(self, key) -> int:
        """
        Delete a key from the cache, failing silently.
        """
        return await self.store.delete(self.make_key(key))

    async def keys(self, pattern="*") -> list[bytes]:
        """
        Delete a key from the cache, failing silently.
        """
        return await self.store.keys(self.make_key(pattern))

    # async def clear(self):
    #     """Remove *all* values from the cache at once."""
    #     raise NotImplementedError(
    #         "subclasses of BaseCache must provide a clear() method"
    #     )

    # async def close(self, **kwargs):
    #     """Close the cache connection"""
    #     await self.store.close()
