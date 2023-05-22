import pytest

from mobilex import App, Request
from mobilex.cache.dict import DictCache
from mobilex.cache.redis import RedisCache
from mobilex.response import redirect
from mobilex.router import UssdRouter
from mobilex.screens import CON, END, Screen
from mobilex.sessions import SessionManager


@pytest.mark.parametrize("session_backend", [DictCache, RedisCache])
async def test_basic(session_backend, fake_redis):
    app = App(session_backend=session_backend)

    router = UssdRouter("test")

    @router.start_screen("index")
    class Index(Screen):
        def render(self):
            return redirect("home")

    @router.screen("home")
    class Home(Screen):
        async def handle(self, val):
            self.print(f"Your value was {val}")
            return END

        async def render(self):
            self.print("Hello world")
            return CON

    app.include_router(router)
    app.setup()

    req_0 = Request("123456")
    res_0: str = await app.adispatch(req_0)
    assert res_0.partition("\n")[0] == f"{CON} Hello world"

    val = "xyz"
    req_1 = Request(f"123456", ussd_string="xyz")
    res_1 = await app.adispatch(req_1)
    assert res_1.partition("\n")[0] == f"{END} Your value was {val}"
