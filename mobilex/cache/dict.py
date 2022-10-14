import asyncio
import typing as t

from datetime import timedelta

try:
    from cachetools import TTLCache    
except ImportError:
    raise ImportError(
        f"{__name__!r} requires 'cachetools' installed. `pip install cachetools`"
    )


from .base import BaseCache



loop = asyncio.get_event_loop()


class DictCache(BaseCache):
    
    store: TTLCache

    async def setup(self, app):
        self.store = TTLCache(1024, self.default_timeout)

    async def add(self, key, value, timeout=..., version=None) -> bool:
        """
        Set a value in the cache if the key does not already exist. If
        timeout is given, use that timeout for the key; otherwise use the
        default cache timeout.

        Return True if the value was stored, False otherwise.
        """
        sk = self.make_key(key, version)
        if rv := not sk in self.store:
            self.store[sk] = self.dumps(value)
        return rv

    async def get(self, key, version=None) -> t.Any:
        """
        Fetch a given key from the cache. If the key does not exist, return
        default, which itself defaults to None.
        """
        rv = self.store.get(self.make_key(key, version))
        return rv if rv is None else self.loads(rv)

    async def set(self, key, value, timeout=..., version=None) -> bool:
        """
        Set a value in the cache. If timeout is given, use that timeout for the
        key; otherwise use the default cache timeout.
        """
        self.store[self.make_key(key, version)] = self.dumps(value)
        return True

    async def delete(self, key, version=None) -> int:
        """
        Delete a key from the cache, failing silently.
        """
        return +(not self.store.pop(self.make_key(key, version), None) is None)

    async def keys(self, pattern='*', version=None) -> int:
        """
        Delete a key from the cache, failing silently.
        """
        return self.store.keys()

    async def clear(self):
        """Remove *all* values from the cache at once."""
        self.store.clear()

    async def close(self, **kwargs):
        """Close the cache connection"""
        self.store.clear()
