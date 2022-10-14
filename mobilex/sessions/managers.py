import abc
import asyncio
import typing as t
from collections import namedtuple

from ..utils.uri import Uri
from .core import History, Session

if t.TYPE_CHECKING:
    from mobilex import FlexUssd
    from mobilex.cache.base import BaseCache



class SessionManager(abc.ABC):

    app: 'FlexUssd'
    session_class: t.Type[Session] = Session

    def __init__(self, backend: 'BaseCache', app: 'FlexUssd' = None):
        self.app = app
        self.backend: 'BaseCache' = backend

    async def setup(self, app: 'FlexUssd'):
        self.app = app
        await self.backend.setup(app)

    # @property
    # def backend(self):
    # 	from django.core.cache import cache
    # 	return cache

    @property
    def session_ttl(self):
        return self.app.config.SESSION_TIMEOUT

    @property
    def key_prefix(self):
        return self.app.config.SESSION_KEY_PREFIX

    # def get_session_key(self, request):
    # 	return self.session_key_class(
    # 			msisdn=request.msisdn, 
    # 			ident=str(request.session_id or '')
    # 		)

    # def is_alive(self, session: Session) -> bool:
    # 	return session.age < self.session_ttl

    def create_new_session(self, request) -> Session:
        return self.session_class(
                self.session_ttl, 
                request.msisdn, 
                request.session_id
            )

    async def get_saved_session(self, request):
        return await self.backend.get(self.make_key(request.msisdn))

    async def save_session(self, session, request):
        return await self.backend.set(self.make_key(session.msisdn), session, self.session_ttl*2)

    async def open_session(self, request):
        request.session = session = (await self.get_saved_session(request))\
                or self.create_new_session(request)
        
        # if session.key != key or not self.is_alive(session):
        # 	session.restored = session.key
        # 	session.key = key
            
        await session.start_request(request)
        request.history = History(HistoryManager(self, session), session.get('_statestack'))

    async def close_session(self, request, response):
        session = request.session
        session['_statestack'] = request.history.stack
        await session.finish_request(request)
        asyncio.create_task(self.save_session(session, request))

    def make_key(self, *parts, prefix=None):
        if prefix:
            return Uri(self.key_prefix, prefix, *parts)
        else:
            return Uri(self.key_prefix, *parts)
        # prefix = ':'.join(filter(None, (self.key_prefix, prefix)))
        # rv = self.key_sep.join(map(str, parts))
        # return f'{prefix}{self.key_sep}{rv}' if prefix else rv




class HistoryManager(object):

    key_prefix = 'state'
    
    def __init__(self, session_manager: SessionManager, session: Session):
        self.session = session
        self.session_manager = session_manager

    @property
    def backend(self):
        return self.session_manager.backend	

    @property
    def state_ttl(self):
        mgr = self.session_manager
        return mgr.session_ttl * mgr.app.config.SCREEN_STATE_LIFETIMES
    
    async def load_state(self, key):
        return await self.backend.get(self.make_key(key))

    async def save_state(self, key, state):
        return await self.backend.set(self.make_key(key), state, self.state_ttl)
    
    def make_key(self, *parts):
        return self.session_manager.make_key(self.session.pk, *parts, prefix=self.key_prefix)
