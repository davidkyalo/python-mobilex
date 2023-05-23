import asyncio
import re
import typing as t
from datetime import timedelta

try:
    from cachetools import TTLCache
except ImportError:  # pragma: no cover
    raise ImportError(
        f"{__name__!r} requires 'cachetools' installed. `pip install cachetools`"
    )

from .base import BaseCache

if t.TYPE_CHECKING:
    from mobilex import App


class DictCache(BaseCache):
    store: TTLCache

    def __init__(self, app: "App", location=None, **options):
        super().__init__(app, **options)
        self.store = TTLCache(1024, self.ttl.total_seconds())

    async def get(self, key) -> t.Any:
        """
        Fetch a given key from the cache. If the key does not exist, return
        default, which itself defaults to None.
        """
        if (rv := self.store.get(self.make_key(key))) is not None:
            rv = self.loads(rv)
        return rv

    async def set(self, key, value) -> bool:
        """
        Set a value in the cache. If timeout is given, use that timeout for the
        key; otherwise use the default cache timeout.
        """
        self.store[self.make_key(key)] = self.dumps(value)
        return True

    async def delete(self, key) -> int:
        """
        Delete a key from the cache, failing silently.
        """
        return +(not self.store.pop(self.make_key(key), None) is None)

    async def keys(self, key="*"):
        """
        Delete a key from the cache, failing silently.
        """
        key = b".*".join(re.escape(p) for p in self.make_key(key).split(b"*") if p)
        p_re = key and re.compile(key)
        return [k for k in self.store.keys() if not p_re or p_re.search(k)]

    # async def clear(self):
    #     """Remove *all* values from the cache at once."""
    #     self.store.clear()

    # async def close(self, **kwargs):
    #     """Close the cache connection"""
    #     self.clear()
