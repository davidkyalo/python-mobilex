import asyncio
import logging
import typing as t

from collections import defaultdict


from .utils import ArgumentVector
from .screens import CON, END
from .const import ResponseType

from .response import Response, RedirectResponse
from .screens.registry import ScreenRegistry


logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:
    from . import FlexUssd, Response, Request



class UssdRouter:

    parent: 'FlexUssd'

    def __init__(self, name):
        self.name = name
        self._registry = defaultdict(ScreenRegistry)
        self._start_screen = None

    @property
    def _home_screen(self):
        try:
            return self.__dict__['_home_screen']
        except KeyError:
            return self._start_screen
    
    @_home_screen.setter
    def _home_screen(self, value):
        self.__dict__['_home_screen'] = value
    
    @property
    def config(self):
        return self.parent.config
    
    def run_embeded(self, parent):
        self.parent = parent

    def screen(self, name: str):
        def decorator(screen):
            nonlocal name, self
            self.register_screen(name, screen)
            return screen
        return decorator
    
    def register_screen(self, name: str, screen: t.Any):
        self._registry[''].set(name, screen)
        return screen

    def start_screen(self, name: str):
        def decorator(screen):
            nonlocal name, self
            self.register_start_screen(name, screen)
            return screen
        return decorator
    
    def register_start_screen(self, name: str, screen: t.Any):
        self._start_screen = name, screen
        return self.register_screen(name, screen)

    def home_screen(self, name: str):
        def decorator(screen):
            nonlocal name, self
            self.register_home_screen(name, screen)
            return screen
        return decorator
    
    def register_home_screen(self, name: str, screen: t.Any):
        self._home_screen = name, screen
        return self.register_screen(name, screen)

    def get_screen(self, name: str, default=...):
        rkey, key = name.split('.', 1)
        if (reg := self._registry.get('' if rkey == self.name else rkey)):
            return reg.get(key, default)
        elif default is ...:
            raise LookupError(f'UssdScreen {name!r} not found')
        return default

    def get_all_screens(self, name: str, default=...):
        rkey, key = name.split('.', 1)
        if (reg := self._registry.get('' if rkey == self.name else rkey)):
            return reg.getall(key, default)
        elif default is ...:
            raise LookupError(f'UssdScreen {name!r} not found')
        return default

    def get_start_screen(self, *, withname=False):
        name, screen = self._start_screen
        return (f'{self.name}.{name}', screen) if withname else screen
    
    def get_home_screen(self, *, withname=False):
        name, screen = self._home_screen
        return (f'{self.name}.{name}', screen) if withname else screen
    
    def abs_screen_name(self, name: str):
        return f'{self.name}{name}' if name[0] == 0 else name

    def _eval_argv(self, request: 'Request') -> 'Response':
        session = request.session
        argv = ArgumentVector(
            service_code=request.service_code,
            argstr=request.ussd_string,
            base_code=request.initial_code
        )
        
        if session.is_stale or not (oldargv := session.argv):
            request.args = argv.args
        else:
            request.args = argv - oldargv

        session.argv = argv

    async def pre_request(self, request: 'Request') -> 'Response':
        request.app = self
        self._eval_argv(request)

    async def post_request(self, request: 'Request', response: 'Response') -> 'Response':
        return response

    def create_new_state(self, name, screen):
        cls = screen.Meta.state_class
        return cls(name)

    def create_screen(self, state, request: 'Request'):
        cls = self.get_screen(state.screen)
        rv = cls(state)
        return rv

    async def dispatch_request(self, request):

        session = request.session
        state = session.state

        if session.restored:
            screen = self.get_screen(state.screen)
            if request.args or not screen._meta.restore_sessions:
                session.reset()

        if session.is_new:
            name, screen = self.get_start_screen(withname=True)
            state = session.state = self.create_new_state(name, screen)
            inpt, args = None, request.args
        else:
            inpt, *args = request.args or (None,)

        if state is None:
            raise RuntimeError('Screen state cannot be None.')

        rv = await self.dispatch_to_screen(request, state, inpt, *args)
        return rv

    async def dispatch_to_screen(self, request: 'Request', state, inpt=None, /, *args):
        screen = self.create_screen(state, request)
        
        try:
            res = await screen(request, inpt)
        except Exception as e:
            logger.exception(e)
            raise e

        if isinstance(res, RedirectResponse):
            if res.type == ResponseType.POP:
                if res.to == 0 or not (ores := await request.history.pop(res.to)):
                    n, s = self.get_home_screen(withname=True)
                    state = request.session.state = self.create_new_state(n, s)
                    state.update(res.ctx)
                else:
                    n, s = ores.to, self.get_screen(ores.to) 
                    state = request.session.state = self.create_new_state(n, s)
                    state.update(ores.ctx)
                    state.update(res.ctx)
                return await self.dispatch_to_screen(request, state, *args)
            else:
                n = res.to = self.abs_screen_name(res.to)
                s = self.get_screen(n)
                state = request.session.state = self.create_new_state(n, s)
                state.update(res.ctx)

                await request.history.push(res)
                res.content is None or (args := (res.content,) + args) 
                return await self.dispatch_to_screen(request, state, *args)
    
        request.session.state = screen.state
        
        if res in (CON, END):
            return f'{res} {screen.payload}'
        elif isinstance(res, tuple):
            return ' '.join(res)
        elif isinstance(res, str):
            return res
        print('*'*30, f'RESPONSE --> {res}')
        raise RuntimeError('Screen must return Response object or string.')

    async def __call__(self, request, *args, **kwargs):
        response = await self.pre_request(request)
        response is None and (response := await self.dispatch_request(request))
        return await self.post_request(request, response) or response
