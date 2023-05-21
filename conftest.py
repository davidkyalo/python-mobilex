from unittest.mock import PropertyMock, patch
import pytest


def pytest_configure(config):
    pass


from fakeredis.aioredis import FakeRedis


@pytest.fixture
def fake_redis():
    from mobilex.cache.redis import RedisCache

    store = PropertyMock(return_value=FakeRedis())
    with patch.object(RedisCache, "store", store, create=True):
        yield
