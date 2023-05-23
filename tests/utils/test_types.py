from unittest.mock import Mock

import pytest

from mobilex.utils.types import FrozenNamespaceDict, NamespaceDict


def test_FrozenNamespaceDict():
    vals = dict(abc=Mock(), xyz=Mock())
    obj = FrozenNamespaceDict(vals)

    assert obj
    assert all(k in obj for k in vals)
    assert obj.abc is obj["abc"]

    assert dict(obj) == vals
    assert obj.__json__() == vals
    assert vars(obj) == vals
    with pytest.raises(KeyError):
        obj["123"]

    with pytest.raises(AttributeError):
        obj.abc = "123"

    with pytest.raises(AttributeError):
        del obj.xyz


def test_NamespaceDict():
    vals = dict(abc=Mock(), xyz=Mock())
    obj = NamespaceDict(vals)

    assert obj
    assert all(k in obj for k in vals)
    assert dict(obj) == vals

    mk = Mock()
    obj["abc"] = mk
    assert obj.abc is mk is obj["abc"]

    obj["new"] = mk
    assert obj.new is mk is obj["new"]
    assert "new" in obj
    del obj["new"]
    assert "new" not in obj
    with pytest.raises(KeyError):
        del obj["new"]
