import typing as t  


_T = t.TypeVar('_T')


class class_property(t.Generic[_T]):

    def __init__(self, getter=None, setter=None):
        if getter is not None and not isinstance(getter, classmethod):
            getter = classmethod(getter)
        if setter is not None and not isinstance(setter, classmethod):
            setter = classmethod(setter)
        self.__get = getter
        self.__set = setter

        info = getter.__get__(object)  # just need the info attrs.
        self.__doc__ = info.__doc__
        self.__name__ = info.__name__
        self.__module__ = info.__module__

    def __get__(self, obj, type=None) -> _T:
        if not obj is None and type is None:
            type = obj.__class__
        return self.__get.__get__(obj, type)()

    def __set__(self, obj, value: _T):
        if obj is None:
            return self
        return self.__set.__get__(obj)(value)

    def setter(self, setter):
        return self.__class__(self.__get, setter)
