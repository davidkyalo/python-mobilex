import pickle
import typing as t
from collections import abc
from datetime import timedelta

from mobilex.utils import to_bytes, to_timedelta

if t.TYPE_CHECKING:
    from mobilex import App

CacheKey = t.NewType("CacheKey", str)

Timeout = t.Union[int, float, timedelta]


class BaseCache:
    app: "App"
    ttl: timedelta
    key_prefix: bytes
    options: abc.Mapping[str, t.Any]

    def __init_subclass__(cls) -> None:
        cls._has_dump = cls.__dict__.get("dumps") is not None
        cls._has_loads = cls.__dict__.get("loads") is not None
        super().__init_subclass__()

    def __init__(
        self,
        app: "App" = None,
        *,
        ttl: Timeout = None,
        key_prefix: str | bytes = None,
        serializer=pickle,
        **opts,
    ):
        serializer, ttl = serializer or pickle, to_timedelta(ttl or 600)
        self.app, self.ttl, self.serializer, self.options = app, ttl, serializer, opts

        prefix = b"|".join(map(to_bytes, filter(None, (app and app.name, key_prefix))))
        self.key_prefix = prefix and prefix + b"|"
        assert b"*" not in self.key_prefix, f"key_prefix cannot contain '*'"
        if not self._has_dump:
            self.dumps = serializer.dumps
        if not self._has_loads:
            self.loads = serializer.loads

    def make_key(self, key: t.Any):
        kb = key if isinstance(key, bytes) else str(key).encode()
        return b"%b|%b" % (self.key_prefix, kb)

    # def get_ttl(self, timeout=...):
    #     """Return the timeout value usable by this backend based upon the provided
    #     timeout.
    #     """
    #     return self.ttl if timeout is ... else timeout

    def dumps(self, obj):  # pragma: no cover
        return self.serializer.dumps(obj)

    def loads(self, obj):  # pragma: no cover
        return self.serializer.loads(obj)

    async def add(self, key, value):
        """
        Set a value in the cache if the key does not already exist. If
        timeout is given, use that timeout for the key; otherwise use the
        default cache timeout.

        Return True if the value was stored, False otherwise.
        """
        raise NotImplementedError(
            "subclasses of BaseCache must provide an add() method"
        )

    async def keys(self, pattern="*") -> list[bytes]:
        raise NotImplementedError(
            "subclasses of BaseCache must provide a keys() method"
        )

    async def get(self, key):
        """
        Fetch a given key from the cache. If the key does not exist, return
        default, which itself defaults to None.
        """
        raise NotImplementedError("subclasses of BaseCache must provide a get() method")

    async def set(self, key, value):
        """
        Set a value in the cache. If timeout is given, use that timeout for the
        key; otherwise use the default cache timeout.
        """
        raise NotImplementedError("subclasses of BaseCache must provide a set() method")

    async def delete(self, key):
        """
        Delete a key from the cache, failing silently.
        """
        raise NotImplementedError(
            "subclasses of BaseCache must provide a delete() method"
        )

    async def clear(self):
        """Remove *all* values from the cache at once."""
        raise NotImplementedError(
            "subclasses of BaseCache must provide a clear() method"
        )

    async def close(self, **kwargs):
        """Close the cache connection"""
        raise NotImplementedError(
            "subclasses of BaseCache must provide a close() method"
        )
