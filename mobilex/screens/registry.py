import weakref
import typing as t 

if t.TYPE_CHECKING:
    from .base import Screen





class ScreenRegistry:
    """ScreenRegistry doc"""

    __slots__ = '_screens', '_remove', '__weakref__',

    _screens: dict[str, list[type['Screen']]] 

    def __init__(self):
        self._screens = dict()
        def remove(wr: weakref.KeyedRef, selfref=weakref.ref(self)):
            if self := selfref():
                self._screens[wr.key].remove(wr)
        self._remove = remove
            
    def get(self, name, default=...):
        try:
            return next(self._getall(name, reverse=True))
        except KeyError:
            if default is ...:
                raise LookupError(name)
            return default
    
    def _getall(self, name, *, reverse=False, strict=True):
        ls = self._screens[name]
        for yv in (r() for r in (reversed(ls) if reverse else ls)):
            if not yv is None:
                yield yv
                strict = False
        if strict:
            raise KeyError(name)
    
    def getall(self, name, default=...):
        try:
            return list(self._getall(name))
        except KeyError:
            if default is ...:
                raise LookupError(name)
            return default
    
    def set(self, name, screen):
        wr = weakref.KeyedRef(screen, self._remove, name)
        self._screens.setdefault(name, []).append(wr)


_REGISTRY = ScreenRegistry()

registry = _REGISTRY

