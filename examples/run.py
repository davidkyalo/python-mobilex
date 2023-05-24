import asyncio
import logging

asyncio.get_event_loop().set_debug(True)

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("asyncio").setLevel(logging.DEBUG)
logging.getLogger("requests").setLevel(logging.INFO)

from fastapi import Depends, FastAPI
from starlette.responses import PlainTextResponse

from mobilex import App
from mobilex import Request as UssdRequest

from .shopping_cart.screens import router

api = FastAPI(debug=True)

app = App()
app.include_router(router)
app.setup()


@api.get("/ussd/", response_class=PlainTextResponse)
async def entry(request: UssdRequest = Depends()):
    return await app(request)
