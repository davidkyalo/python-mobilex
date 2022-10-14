



class Uri(tuple):

    __slots__ = ()

    _sep = "/"

    def __new__(cls, path=None, *paths):
        if not paths and isinstance(path, cls):
            return path
        return super().__new__(cls, cls._parse(path, *paths))

    @property
    def parts(self):
        return tuple(self)

    def as_str(self):
        return str(self)

    @classmethod
    def _parse(cls, *paths):
        for path in paths:
            if isinstance(path, Uri):
                yield from path
            else:
                for p in path.split(cls._sep) if isinstance(path, str) else path:
                    if not isinstance(p, (str, int, float)):
                        raise TypeError("Uri can only contain strings. %s" % type(p))
                    elif p or p == 0:
                        yield str(p)

    def startswith(self, other, start=None, end=None):
        if not isinstance(other, tuple):
            other = self.__class__(other)

        target = self if start is None and end is None else self[start:end]
        olen, tlen = len(other), len(target)
        if tlen == olen:
            return target == other
        elif tlen > olen:
            return target[:olen] == other
        else:
            return False

    def endswith(self, other, start=None, end=None):
        if not isinstance(other, tuple):
            other = self.__class__(other)

        target = self if start is None and end is None else self[start:end]
        olen, tlen = len(other), len(target)
        if tlen == olen:
            return target == other
        elif tlen > olen:
            return target[(olen * -1) :] == other
        else:
            return False

    def copy(self):
        return self.__class__(iter(self))

    def join(self, *paths):
        return self.__class__(self, *paths)

    def __contains__(self, value):
        value = self.__class__(value)
        lv, ls = len(value), len(self)
        if lv == 0:
            return True
        elif ls == 0 or lv > ls:
            return False
        elif ls == lv:
            return self == value
        else:
            return str(value) in str(self)

    def __eq__(self, other):
        """Check equality against strings, lists and tuples.
		"""
        if isinstance(other, (str, Uri)):
            return str(self) == str(other)
        else:
            return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def __add__(self, other):
        return self.__class__(self, other)

    def __mul__(self, other):
        if isinstance(other, int):
            return self.__class__(*(self for _ in range(other)))
        return super().__mul__(other)

    def __hash__(self):
        return hash(str(self))

    def __getitem__(self, index):
        rv = super().__getitem__(index)
        if isinstance(index, slice):
            return self.__class__(rv)
        else:
            return rv

    def __json__(self):
        return self.as_str()

    def __str__(self):
        return self._sep.join(self)
        # try:
        #     return self._str
        # except AttributeError:
        #     self._str = self._sep.join(self)
        #     return self._str

    def __repr__(self):
        return '%s("%s")' % (self.__class__.__name__, self)


uri = Uri



# class UriField(models.CharField):

#     description = "A slash '/' separated path"

#     # def __init__(self, *args, **kwargs):
#     # 	kwargs.setdefault('max_length', 255)
#     # 	super().__init__(*args, **kwargs)

#     def to_python(self, value):
#         return None if value is None else Uri(value)

#     def from_db_value(self, value, expression, connection, context=None):
#         return self.to_python(value)

#     def get_prep_value(self, value):
#         return self.to_python(value)
