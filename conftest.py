from unittest.mock import PropertyMock, patch

import pytest


def pytest_configure(config):
    pass


from fakeredis.aioredis import FakeRedis


@pytest.fixture(autouse=True)
def fake_redis(request: pytest.FixtureRequest):
    from mobilex.cache.redis import RedisCache

    if mk := request.node.get_closest_marker("real_redis"):
        if not mk.args or mk.args[0] == True:
            return

    store = PropertyMock(return_value=FakeRedis())
    with patch.object(RedisCache, "store", store, create=True):
        yield


@pytest.fixture
def app_config(request: pytest.FixtureRequest):
    res, vars = {}, [
        "max_page_length",
        "session_class",
        "session_key_prefix",
        "session_backend",
        "session_manager",
        "session_ttl",
        "history_class",
        "history_backend",
        "history_key_prefix",
        "history_ttl",
    ]
    for key in vars:
        try:
            res[key] = request.getfixturevalue(f"{key}_config")
        except pytest.FixtureLookupError:
            pass
    return res


@pytest.fixture
async def app(app_config: dict):
    from mobilex import App

    app = App()
    app.configure(app_config)

    yield app

    for back in (app.session_backend, app.history_backend):
        for key in await back.keys():
            await back.delete(key)


@pytest.fixture
def router(app):
    yield app.router
