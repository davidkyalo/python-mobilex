import typing as t
from collections import abc
from copy import deepcopy

from typing_extensions import Self

_T_Key = t.TypeVar("_T_Key", bound=abc.Hashable)
_T_Val = t.TypeVar("_T_Val")

_T_Pk = t.TypeVar("_T_Pk", bound=abc.Hashable)


_object_new = object.__new__
_object_setattr = object.__setattr__


class FallbackDict(dict[_T_Key, _T_Val]):

    __slots__ = ()

    def __missing__(self, key):
        return None



class ReadonlyDict(dict[_T_Key, _T_Val]):
    """A readonly `dict` subclass.

    Raises:
        TypeError: on any attempted modification
    """

    __slots__ = ()

    def not_mutable(self, *a, **kw):
        raise TypeError(f"readonly type: {self} ")

    __delitem__ = __setitem__ = setdefault = not_mutable
    clear = pop = popitem = update = __ior__ = not_mutable
    del not_mutable

    @classmethod
    def fromkeys(cls, it: abc.Iterable[_T_Key], value: _T_Val = None):
        return cls((k, value) for k in it)

    def __reduce__(self):
        return (
            self.__class__,
            (dict(self),),
        )

    def copy(self):
        return self.__class__(self)

    __copy__ = copy

    def __deepcopy__(self, memo=None):
        return self.__class__(deepcopy(dict(self), memo))

    __or = dict[_T_Key, _T_Val].__or__

    def __or__(self, o):
        r = self.__or(o)
        if r.__class__ is dict:
            return self.__class__(r)
        return r


class FrozenDict(ReadonlyDict[_T_Key, _T_Val]):
    """An hashable `ReadonlyDict`"""

    __slots__ = ("_v_hash",)

    def __hash__(self):
        try:
            ash = self._v_hash
        except AttributeError:
            ash = None
            items = self._eval_hashable()
            if items is not None:
                try:
                    ash = hash(items)
                except TypeError:
                    pass
            _object_setattr(self, "_v_hash", ash)

        if ash is None:
            raise TypeError(f"un-hashable type: {self.__class__.__name__!r}")

        return ash

    def _eval_hashable(self) -> abc.Hashable:
        return (*((k, self[k]) for k in sorted(self)),)




class FrozenAttributeMapping(abc.Mapping[_T_Key, _T_Val]):
    """Provides mapping access to object attributes."""

    __slots__ = '__dict__',

    def __len__(self) -> int:
        return len(getattr(self, "__dict__", "-"))

    def __contains__(self, o: _T_Key) -> bool:
        return hasattr(self, o)

    def __iter__(self):
        return iter(self.__dict__)

    def __json__(self):
        return dict(self)

    def __getitem__(self, k: _T_Key) -> _T_Val:
        try:
            return getattr(self, k)
        except AttributeError:
            return self.__missing__(k)

    def __missing__(self, key: _T_Key):
        raise KeyError(key)


class AttributeMapping(FrozenAttributeMapping[_T_Key, _T_Val], abc.MutableMapping[_T_Key, _T_Val]):

    __slots__ = ()
    _pos_args: t.ClassVar[tuple[str]] = ()

    def __init__(self, *args, **kwds) -> None:
        (args or kwds) and self.update(*args, **kwds)

    def __delitem__(self, k):
        try:
            return delattr(self, k)
        except AttributeError as e:
            raise KeyError(k) from e

    def __setitem__(self, k, v) -> None:
        return setattr(self, k, v)
