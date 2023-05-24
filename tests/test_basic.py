from unittest.mock import Mock

import pytest

from mobilex import App, Request
from mobilex.cache.dict import DictCache
from mobilex.cache.redis import RedisCache
from mobilex.exc import ScreenNotFoundError
from mobilex.responses import redirect
from mobilex.router import Router
from mobilex.screens import CON, END, Action, Screen


@pytest.mark.parametrize("session_backend_config", [DictCache, RedisCache])
async def test_basic(app: App, router: Router, session_backend_config):
    @app.entry_screen("index")
    class Index(Screen):
        nav_actions = [
            Action("Go Home", screen="home"),
        ]

    @app.home_screen("home")
    class Home(Screen):
        async def handle(self, val):
            self.print(f"Your value was {val}")
            return END

        async def render(self):
            return redirect("end")

    @app.screen("end")
    class End(Screen):
        async def handle(self, val):
            return redirect(-1, val)

        async def render(self):
            self.print("Hello world")
            return CON

    req_0 = Request("123456")
    res_0: str = await app(req_0)
    assert res_0.startswith(f"{CON} \n1  Go Home")

    req_1 = Request("123456", ussd_string="1")
    res_1: str = await app(req_1)
    assert res_1.startswith(f"{CON} Hello world")

    val = "xyz"
    req_2 = Request(f"123456", ussd_string="1*xyz")
    res_2: str = await app(req_2)

    # assert res_2.startswith(f"{END} Your value was {val}")

    with pytest.raises(ScreenNotFoundError):
        router.get_screen("xyz")
