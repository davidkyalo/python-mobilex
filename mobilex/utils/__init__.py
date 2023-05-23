import re
import typing as t
from collections import abc
from datetime import timedelta

_ussd_split_re = r"\*(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)"


def to_bytes(obj):
    return obj if isinstance(obj, bytes) else str(obj).encode()


def to_timedelta(
    val: int | float | timedelta | None, *, resolution: timedelta = timedelta(seconds=1)
):
    return val if isinstance(val, timedelta) else (val or 0) * resolution


def split_argstr(s):
    return re.split(_ussd_split_re, s) if s else ()


class ArgumentVector(list[str]):
    __slots__ = ()

    def __init__(
        self,
        iterable: t.Optional[abc.Iterable[str]] = None,
        *,
        service_code=None,
        argstr: str = None,
        base_code=None
    ):
        if argstr is not None:
            if base_code and argstr.startswith(base_code):
                argstr = argstr[len(base_code) :].lstrip("*")
                if service_code:
                    service_code = "*".join((service_code, base_code))
            iterable = (s.replace('"', "") for s in split_argstr(argstr))

        super().__init__(() if iterable is None else iterable)
        argstr is None or self.insert(0, service_code or "")

    @property
    def service_code(self):
        return self[0].split("*", 1)[0]

    @property
    def base_code(self):
        return self[0].split("*", 1)[1] if "*" in self[0] else ""

    @property
    def args(self):
        return self[1:]

    def __sub__(self, other):
        if not isinstance(other, ArgumentVector):  # pragma: no cover
            return NotImplemented

        ld = len(self) - len(other)

        return self[-ld:] if ld > 0 and self[:-ld] == other else []

    def __str__(self):
        return "%s" % "*".join(self)

    def __repr__(self):
        return "<ArgumentVector: %s>" % (self,)
