import os
import django
import uvloop
import typing as t


uvloop.install()


import asyncio


from fastapi import FastAPI, Depends
from starlette.responses import Response


from mobilex import App, Request as UssdRequest
from mobilex.sessions import SessionManager
from mobilex.cache.redis import RedisCache

loop = asyncio.get_event_loop()

app = FastAPI()

cache = RedisCache()

ussd_app = App(session_manager=SessionManager(cache), config={})

from .shopping_cart.screens import router

ussd_app.include_router(router)


@app.get(
    "/ussd/", response_class=Response, responses={200: {"content": {"text/plain": {}}}}
)
async def ussd_view(request: UssdRequest = Depends()):
    res = await ussd_app(request)
    return res


loop.set_debug(True)


import logging

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("asyncio").setLevel(logging.DEBUG)
logging.getLogger("requests").setLevel(logging.INFO)

asyncio.ensure_future(ussd_app.run())
