import typing as t
from collections import abc
from typing import Any

_T_Key = t.TypeVar("_T_Key", bound=abc.Hashable)
_T_Val = t.TypeVar("_T_Val")


class FrozenNamespaceDict(abc.Mapping[_T_Key, _T_Val]):
    """Provides mapping access to object attributes."""

    __slots__ = ("__dict__", "__weakref__")

    def __init__(self, *args, **kwds) -> None:
        self.__dict__.update(*args, **kwds)

    def __len__(self) -> int:
        return len(self.__dict__)

    def __contains__(self, o: _T_Key) -> bool:
        return hasattr(self, o)

    # def __dir__(self) -> abc.Iterable[str]:
    #     return iter(self.__dict__)

    def __iter__(self):
        return iter(self.__dict__)

    def __json__(self):
        return vars(self)

    def __getitem__(self, k: _T_Key) -> _T_Val:
        try:
            return getattr(self, k)
        except AttributeError:
            return self.__missing__(k)

    def __setattr__(self, name: str, value: Any) -> None:
        cls = self.__class__
        raise AttributeError(f"cannot set attribute {name!r} on {cls.__name__!r}")

    def __delattr__(self, name: str) -> None:
        cls = self.__class__
        raise AttributeError(f"cannot delete attribute {name!r} on {cls.__name__!r}")

    def __missing__(self, key: _T_Key):
        raise KeyError(key)


class NamespaceDict(
    FrozenNamespaceDict[_T_Key, _T_Val], abc.MutableMapping[_T_Key, _T_Val]
):
    __slots__ = ()
    _pos_args: t.ClassVar[tuple[str]] = ()

    __setattr__ = object.__setattr__
    __delattr__ = object.__delattr__

    def __init__(self, *args, **kwds) -> None:
        (args or kwds) and self.update(*args, **kwds)

    def __delitem__(self, k):
        try:
            return delattr(self, k)
        except AttributeError as e:
            raise KeyError(k) from e

    def __setitem__(self, k, v) -> None:
        return setattr(self, k, v)
