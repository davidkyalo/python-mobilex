from importlib import import_module
from operator import attrgetter
import pickle
import typing as t

from datetime import timedelta

from mobilex.utils.uri import Uri


if t.TYPE_CHECKING:
    from mobilex import FlexUssd 

CacheKey = t.NewType('CacheKey', str)

AnyKey = t.Union[str, Uri, t.Tuple[t.Union[str, Uri], ...]]
Timeout = t.Union[int, float, timedelta]
Version = t.NewType('Version', int)
KeyFunc = t.Union[t.Callable[[AnyKey, AnyKey, Version], CacheKey], str]


def default_key_func(key: AnyKey, prefix: AnyKey, version: Version) -> CacheKey:
    """
    Default function to generate keys.

    Construct the key used by all other methods. By default, prepend
    the `prefix'. KEY_FUNCTION can be used to specify an alternate
    function with custom key making behavior.
    """
    
    if version is None:
        return str(Uri(key)) if prefix is None else f'{Uri(prefix)}:{Uri(key)}'
    else:
        return f'{version}:{Uri(key)}' if prefix is None \
                else f'{Uri(prefix)}:{version}:{Uri(key)}'


def get_key_func(key_func):
    """
    Function to decide which key function to use.

    Default to ``default_key_func``.
    """
    if key_func is not None:
        if callable(key_func):
            return key_func
        elif isinstance(key_func, str):
            mod, _, nm = key_func.rpartition(':') 
            if not nm:
                mod, _, nm = key_func.rpartition('.') 
            
            return attrgetter(nm)(import_module(mod))
    return default_key_func




class BaseCache:

    def __init__(self, *, timeout: Timeout = 300, key_prefix: AnyKey = None, 
            version: Version = None, serializer=None, key_func: KeyFunc = None, **options):
        
        if isinstance(timeout, timedelta):
            self.default_timeout = timeout.total_seconds()
        elif timeout is None:
            self.default_timeout = None
        else:
            try:
                self.default_timeout = float(timeout)
            except (ValueError, TypeError) as e:
                raise TypeError('timeout must be a number or timedelta') from e
            
        self.key_prefix = key_prefix
        self.version = version
        self.key_func = get_key_func(key_func)
        self.serializer = serializer or pickle
        self.options = options

    def get_timeout(self, timeout=...):
        """Return the timeout value usable by this backend based upon the provided
        timeout.
        """
        if timeout is ...:
            return self.default_timeout
        elif isinstance(timeout, timedelta):
            return timeout.total_seconds()
        else:
            return timeout
            
    def make_key(self, key, version=None):
        """
        Construct the key used by all other methods. By default, use the
        key_func to generate a key (which, by default, prepends the
        `key_prefix' and 'version'). A different key function can be provided
        at the time of cache construction; alternatively, you can subclass the
        cache backend to provide custom key making behavior.
        """
        version is None and (version := self.version)

        return self.key_func(key, self.key_prefix, version)
    
    def dumps(self, obj):
        return self.serializer.dumps(obj)
    
    def loads(self, obj):
        return self.serializer.loads(obj)
    
    async def setup(self, app: 'FlexUssd'):
        pass

    async def add(self, key, value, timeout=..., version=None):
        """
        Set a value in the cache if the key does not already exist. If
        timeout is given, use that timeout for the key; otherwise use the
        default cache timeout.

        Return True if the value was stored, False otherwise.
        """
        raise NotImplementedError('subclasses of BaseCache must provide an add() method')

    async def get(self, key, version=None):
        """
        Fetch a given key from the cache. If the key does not exist, return
        default, which itself defaults to None.
        """
        raise NotImplementedError('subclasses of BaseCache must provide a get() method')

    async def set(self, key, value, timeout=..., version=None):
        """
        Set a value in the cache. If timeout is given, use that timeout for the
        key; otherwise use the default cache timeout.
        """
        raise NotImplementedError('subclasses of BaseCache must provide a set() method')

    # def touch(self, key, timeout=..., version=None):
    # 	"""
    # 	Update the key's expiry time using timeout. Return True if successful
    # 	or False if the key does not exist.
    # 	"""
    # 	raise NotImplementedError('subclasses of BaseCache must provide a touch() method')

    async def delete(self, key, version=None):
        """
        Delete a key from the cache, failing silently.
        """
        raise NotImplementedError('subclasses of BaseCache must provide a delete() method')

    # def get_many(self, keys, version=None):
    # 	"""
    # 	Fetch a bunch of keys from the cache. For certain backends (memcached,
    # 	pgsql) this can be *much* faster when fetching multiple values.

    # 	Return a dict mapping each key in keys to its value. If the given
    # 	key is missing, it will be missing from the response dict.
    # 	"""
    # 	d = {}
    # 	for k in keys:
    # 		val = self.get(k, version=version)
    # 		if val is not None:
    # 			d[k] = val
    # 	return d

    # def get_or_set(self, key, default, timeout=..., version=None):
    # 	"""
    # 	Fetch a given key from the cache. If the key does not exist,
    # 	add the key and set it to the default value. The default value can
    # 	also be any callable. If timeout is given, use that timeout for the
    # 	key; otherwise use the default cache timeout.

    # 	Return the value of the key stored or retrieved.
    # 	"""
    # 	val = self.get(key, version=version)
    # 	if val is None:
    # 		if callable(default):
    # 			default = default()
    # 		if default is not None:
    # 			self.add(key, default, timeout=timeout, version=version)
    # 			# Fetch the value again to avoid a race condition if another
    # 			# caller added a value between the first get() and the add()
    # 			# above.
    # 			return self.get(key, default, version=version)
    # 	return val

    # def has_key(self, key, version=None):
    # 	"""
    # 	Return True if the key is in the cache and has not expired.
    # 	"""
    # 	return self.get(key, version=version) is not None

    # def incr(self, key, delta=1, version=None):
    # 	"""
    # 	Add delta to value in the cache. If the key does not exist, raise a
    # 	ValueError exception.
    # 	"""
    # 	value = self.get(key, version=version)
    # 	if value is None:
    # 		raise ValueError("Key '%s' not found" % key)
    # 	new_value = value + delta
    # 	self.set(key, new_value, version=version)
    # 	return new_value

    # def decr(self, key, delta=1, version=None):
    # 	"""
    # 	Subtract delta from value in the cache. If the key does not exist, raise
    # 	a ValueError exception.
    # 	"""
    # 	return self.incr(key, -delta, version=version)

    # def __contains__(self, key):
    # 	"""
    # 	Return True if the key is in the cache and has not expired.
    # 	"""
    # 	# This is a separate method, rather than just a copy of has_key(),
    # 	# so that it always has the same functionality as has_key(), even
    # 	# if a subclass overrides it.
    # 	return self.has_key(key)

    # def set_many(self, data, timeout=..., version=None):
    # 	"""
    # 	Set a bunch of values in the cache at once from a dict of key/value
    # 	pairs.  For certain backends (memcached), this is much more efficient
    # 	than calling set() multiple times.

    # 	If timeout is given, use that timeout for the key; otherwise use the
    # 	default cache timeout.

    # 	On backends that support it, return a list of keys that failed
    # 	insertion, or an empty list if all keys were inserted successfully.
    # 	"""
    # 	for key, value in data.items():
    # 		self.set(key, value, timeout=timeout, version=version)
    # 	return []

    # def delete_many(self, keys, version=None):
    # 	"""
    # 	Delete a bunch of values in the cache at once. For certain backends
    # 	(memcached), this is much more efficient than calling delete() multiple
    # 	times.
    # 	"""
    # 	for key in keys:
    # 		self.delete(key, version=version)

    async def clear(self):
        """Remove *all* values from the cache at once."""
        raise NotImplementedError('subclasses of BaseCache must provide a clear() method')

    # def incr_version(self, key, delta=1, version=None):
    # 	"""
    # 	Add delta to the cache version for the supplied key. Return the new
    # 	version.
    # 	"""
    # 	if version is None:
    # 		version = self.version

    # 	value = self.get(key, version=version)
    # 	if value is None:
    # 		raise ValueError("Key '%s' not found" % key)

    # 	self.set(key, value, version=version + delta)
    # 	self.delete(key, version=version)
    # 	return version + delta

    # def decr_version(self, key, delta=1, version=None):
    # 	"""
    # 	Subtract delta from the cache version for the supplied key. Return the
    # 	new version.
    # 	"""
    # 	return self.incr_version(key, -delta, version)

    async def close(self, **kwargs):
        """Close the cache connection"""
        pass
