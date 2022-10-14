import typing as t

from .router import UssdRouter
from .utils import ArgumentVector


if t.TYPE_CHECKING:
    from .sessions import Session


class Request:
    args: ArgumentVector
    session: 'Session'

    msisdn: str
    session_id: t.Union[str, int] = None

    service_code: str = None
    initial_code: str = None
    ussd_string: str = ''

    def __init__(self, msisdn: str, *, ussd_string: str = '', session_id: str = None,
                 service_code: str = None, initial_code: str = None):
        self.msisdn = msisdn
        self.session_id = session_id
        self.ussd_string = ussd_string
        self.service_code = service_code
        self.initial_code = initial_code


class Response(object):
    ...


class FlexUssd(object):

    router: UssdRouter

    def __init__(self, *, session_manager):
        self.session_manager = session_manager
        self.session_manager.app = self
        self.has_booted = False
        # self._routers = {}

    @property
    def config(self):
        from .settings import ussd_settings
        return ussd_settings

    def run(self):
        assert not self.has_booted, (
            f'{self.__class__.__name__}.boot() called multiple times.'
        )

        self.router.run_embeded(self)
        
        self.has_booted = True
        return self

    def include_router(self, router, name: t.Optional[str]=None):
        self.router = router

    async def open_session(self, request: Request):
        await self.session_manager.open_session(request)

    async def close_session(self, request: Request, response: Response):
        await self.session_manager.close_session(request, response)

    async def prepare_request(self, request: Request) -> Request:
        await self.open_session(request)

    async def teardown_request(self, request, response):
        await self.close_session(request, response)

    async def __call__(self, request, *args, **kwargs):
        request = await self.prepare_request(request) or request
        response = await self.router(request)
        return await self.teardown_request(request, response) or response
