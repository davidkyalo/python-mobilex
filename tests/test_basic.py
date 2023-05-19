
import pytest
import typing as t

from mobilex.screens.base import Screen, END


from mobilex import App, Request
from mobilex.router import UssdRouter
from mobilex.sessions import SessionManager
from mobilex.cache.dict import DictCache
from mobilex.response import redirect


async def test_basic():
    

    cache = DictCache()


    app = App(session_manager=SessionManager(cache))

    router = UssdRouter('test')

    @router.start_screen('index')
    class Index(Screen):

        async def render(self, request: 'Request'):
            return redirect('.home')

    @router.screen('home')
    class Home(Screen):

        async def render(self, request: 'Request'):
            self.print('Hello world')
            return END

    app.include_router(router)
    await app.run()

    req = Request('123456')

    res = await app(req)
    print(f' {req = !r} {res = !r}')
    assert res == f'{END} Hello world'