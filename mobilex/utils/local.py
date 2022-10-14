"""Proxy/PromiseProxy implementation.

This module contains critical utilities that needs to be loaded as
soon as possible, and that shall not load any third party modules.

Parts of this module is Copyright by Werkzeug Team.
"""

from collections import abc
import operator
import sys
from functools import reduce
from importlib import import_module
from types import ModuleType
from typing import Any, Generic, ParamSpec, TypeVar, overload

__all__ = ('Proxy', 'PromiseProxy', 'try_import', 'maybe_evaluate')

__module__ = __name__  # used by Proxy class body

_object_new = object.__new__
_object_setattr = object.__setattr__
_object_getattribute = object.__getattribute__
_object_delattr = object.__delattr__

def _default_cls_attr(name, type_, cls_value):
    # Proxy uses properties to forward the standard
    # class attributes __module__, __name__ and __doc__ to the real
    # object, but these needs to be a string when accessed from
    # the Proxy class directly.  This is a hack to make that work.
    # -- See Issue #1087.

    def __new__(cls, getter):
        instance = type_.__new__(cls, cls_value)
        instance.__getter = getter
        return instance

    def __get__(self, obj, cls=None):
        return self.__getter(obj) if obj is not None else self

    return type(name, (type_,), {
        '__new__': __new__, '__get__': __get__,
    })


def try_import(module, default=None):
    """Try to import and return module.

    Returns None if the module does not exist.
    """
    try:
        return import_module(module)
    except ImportError:
        return default


_T_Params = ParamSpec('_T_Params')
_T = TypeVar('_T')
_T_Factory = abc.Callable[_T_Params, _T]

class Proxy(Generic[_T]):
    """Proxy to another object."""

    # Code stolen from werkzeug.local.Proxy.
    __slots__ = ('__local', '__args', '__kwargs', '__dict__')

    __local: abc.Callable[_T_Params, _T]
    __args: tuple
    __kwargs: dict[str, Any] 

    def __new__(cls, local: abc.Callable[_T_Params, _T], /,
                 *args: _T_Params.args, __name__=None, __doc__=None, **kwargs: _T_Params.kwargs):
        self = _object_new(cls)
        _object_setattr(self, '_Proxy__local', local)
        _object_setattr(self, '_Proxy__args', args)
        _object_setattr(self, '_Proxy__kwargs', kwargs)

        if __name__ is not None:
            _object_setattr(self, '__custom_name__', __name__)
        if __doc__ is not None:
            _object_setattr(self, '__doc__', __doc__)
        
        return self

    @_default_cls_attr('name', str, __name__)
    def __name__(self):
        try:
            return self.__custom_name__
        except AttributeError:
            return self._get_current_object().__name__

    @_default_cls_attr('qualname', str, __name__)
    def __qualname__(self):
        try:
            return self.__custom_name__
        except AttributeError:
            return self._get_current_object().__qualname__

    @_default_cls_attr('module', str, __module__)
    def __module__(self):
        return self._get_current_object().__module__

    @_default_cls_attr('doc', str, __doc__)
    def __doc__(self):
        return self._get_current_object().__doc__

    def _get_class(self):
        return self._get_current_object().__class__

    @property
    def __class__(self):
        return self._get_class()

    def _get_current_object(self) -> _T:
        """Get current object.

        This is useful if you want the real
        object behind the proxy at a time for performance reasons or because
        you want to pass the object into a different context.
        """
        loc: abc.Callable[_T_Params, _T] = _object_getattribute(self, '_Proxy__local')
        if not hasattr(loc, '__release_local__'):
            return loc(*self.__args, **self.__kwargs)
        try:  # pragma: no cover
            # not sure what this is about
            return getattr(loc, self.__name__)
        except AttributeError:  # pragma: no cover
            raise RuntimeError(f'no object bound to {self.__name__}')

    @property
    def __dict__(self):
        try:
            return self._get_current_object().__dict__
        except RuntimeError:  # pragma: no cover
            raise AttributeError('__dict__')

    if True:
        def __repr__(self):
            try:
                obj = self._get_current_object()
            except RuntimeError:  # pragma: no cover
                return f'<{self.__class__.__name__} unbound>'
            return repr(obj)

        def __bool__(self):
            try:
                return bool(self._get_current_object())
            except RuntimeError:  # pragma: no cover
                return False

        __nonzero__ = __bool__  # Py2

        def __dir__(self):
            try:
                return dir(self._get_current_object())
            except RuntimeError:  # pragma: no cover
                return []

        def __getattr__(self, name):
            if name == '__members__':
                return dir(self._get_current_object())
            return getattr(self._get_current_object(), name)

        def __setitem__(self, key, value):
            self._get_current_object()[key] = value

        def __delitem__(self, key):
            del self._get_current_object()[key]

        def __setslice__(self, i, j, seq):
            self._get_current_object()[i:j] = seq

        def __delslice__(self, i, j):
            del self._get_current_object()[i:j]

        def __setattr__(self, name, value):
            setattr(self._get_current_object(), name, value)

        def __delattr__(self, name):
            delattr(self._get_current_object(), name)

        def __str__(self):
            return str(self._get_current_object())

        def __lt__(self, other):
            return self._get_current_object() < other

        def __le__(self, other):
            return self._get_current_object() <= other

        def __eq__(self, other):
            return self._get_current_object() == other

        def __ne__(self, other):
            return self._get_current_object() != other

        def __gt__(self, other):
            return self._get_current_object() > other

        def __ge__(self, other):
            return self._get_current_object() >= other

        def __hash__(self):
            return hash(self._get_current_object())

        def __call__(self, *a, **kw):
            return self._get_current_object()(*a, **kw)

        def __len__(self):
            return len(self._get_current_object())

        def __getitem__(self, i):
            return self._get_current_object()[i]

        def __iter__(self):
            return iter(self._get_current_object())

        def __contains__(self, i):
            return i in self._get_current_object()

        def __getslice__(self, i, j):
            return self._get_current_object()[i:j]

        def __add__(self, other):
            return self._get_current_object() + other

        def __sub__(self, other):
            return self._get_current_object() - other

        def __mul__(self, other):
            return self._get_current_object() * other

        def __floordiv__(self, other):
            return self._get_current_object() // other

        def __mod__(self, other):
            return self._get_current_object() % other

        def __divmod__(self, other):
            return self._get_current_object().__divmod__(other)

        def __pow__(self, other):
            return self._get_current_object() ** other

        def __lshift__(self, other):
            return self._get_current_object() << other

        def __rshift__(self, other):
            return self._get_current_object() >> other

        def __and__(self, other):
            return self._get_current_object() & other

        def __xor__(self, other):
            return self._get_current_object() ^ other

        def __or__(self, other):
            return self._get_current_object() | other

        def __div__(self, other):
            return self._get_current_object().__div__(other)

        def __truediv__(self, other):
            return self._get_current_object().__truediv__(other)

        def __neg__(self):
            return -(self._get_current_object())

        def __pos__(self):
            return +(self._get_current_object())

        def __abs__(self):
            return abs(self._get_current_object())

        def __invert__(self):
            return ~(self._get_current_object())

        def __complex__(self):
            return complex(self._get_current_object())

        def __int__(self):
            return int(self._get_current_object())

        def __float__(self):
            return float(self._get_current_object())

        def __oct__(self):
            return oct(self._get_current_object())

        def __hex__(self):
            return hex(self._get_current_object())

        def __index__(self):
            return self._get_current_object().__index__()

        def __coerce__(self, other):
            return self._get_current_object().__coerce__(other)

        def __enter__(self):
            return self._get_current_object().__enter__()

        def __exit__(self, *a, **kw):
            return self._get_current_object().__exit__(*a, **kw)

        def __reduce__(self):
            return self._get_current_object().__reduce__()


class PromiseProxy(Proxy[_T]):
    """Proxy that evaluates object once.

    :class:`Proxy` will evaluate the object each time, while the
    promise will only evaluate it once.
    """

    __slots__ = ('__pending__', '__weakref__')

    def _get_current_object(self):
        try:
            return _object_getattribute(self, '__thing')
        except AttributeError:
            return self.__evaluate__()

    def __then__(self, fun, *args, **kwargs):
        if self.__evaluated__():
            return fun(*args, **kwargs)
        from collections import deque
        try:
            pending = _object_getattribute(self, '__pending__')
        except AttributeError:
            pending = None
        if pending is None:
            pending = deque()
            _object_setattr(self, '__pending__', pending)
        pending.append((fun, args, kwargs))

    def __evaluated__(self):
        try:
            _object_getattribute(self, '__thing')
        except AttributeError:
            return False
        return True

    def __maybe_evaluate__(self):
        return self._get_current_object()

    def __evaluate__(self,
                     _clean=('_Proxy__local',
                             '_Proxy__args',
                             '_Proxy__kwargs')):
        try:
            thing = Proxy._get_current_object(self)
        except Exception:
            raise
        else:
            _object_setattr(self, '__thing', thing)
            for attr in _clean:
                try:
                    _object_delattr(self, attr)
                except AttributeError:  # pragma: no cover
                    # May mask errors so ignore
                    pass
            try:
                pending = _object_getattribute(self, '__pending__')
            except AttributeError:
                pass
            else:
                try:
                    while pending:
                        fun, args, kwargs = pending.popleft()
                        fun(*args, **kwargs)
                finally:
                    try:
                        _object_delattr(self, '__pending__')
                    except AttributeError:  # pragma: no cover
                        pass
            return thing




def maybe_evaluate(obj):
    """Attempt to evaluate promise, even if obj is not a promise."""
    try:
        return obj.__maybe_evaluate__()
    except AttributeError:
        return obj
