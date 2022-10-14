import weakref


class ScreenRegistry:
    """ScreenRegistry doc"""

    def __init__(self, screens=None):
        self._screens = dict() if screens is None else screens

    def get(self, name, default=...):
        try:
            if (rv := self._screens[name][-1]()) is None:
                raise KeyError(name)
            return rv
        except (KeyError, IndexError):
            if default is ...:
                raise LookupError(f'UssdScreen {name!r} not found')
            return default
    
    def getall(self, name, default=...):
        try:
            if not(rv := [r() for r in self._screens[name] if r() is not None]):
                raise KeyError(name)
            return rv
        except KeyError:
            if default is ...:
                raise LookupError(f'UssdScreen {name!r} not found')
            return default
    
    def set(self, name, screen):
        self._screens.setdefault(name, []).append(weakref.ref(screen))


_REGISTRY = ScreenRegistry()

registry = _REGISTRY

