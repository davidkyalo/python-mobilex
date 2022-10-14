from operator import attrgetter
import re
import typing as t
from collections import UserString
from logging import getLogger


from ..utils.types import AttributeMapping
from ..utils.enums import StrChoices


from ..settings import ussd_settings
from ..response import redirect
from .. import exc


if t.TYPE_CHECKING:
    from mobilex import Request, Response, FlexUssd
    from mobilex.sessions import Session


logger = getLogger(__name__)


NOTHING = object()



T = t.TypeVar('T')

CON = 'CON'

END = 'END'


class ScreenMetaOptions:
    pass


class ScreenState(AttributeMapping):
	
    __slots__ = ()

    def __init__(self, screen, *bases, **data):
        super().__init__(*bases, **data)
        self.screen = screen

    def reset(self, *keep, **values):
        ('screen' in keep) or values.setdefault('screen', self.screen)
        for k in keep:
            if k in self:
                values.setdefault(k, getattr(self, k))
        self.clear()
        self.update(values)


class UssdScreenType(type):

    def __new__(mcls, name, bases, dct):
        from .mixins import SyncRenderMixin, SyncHandleMixin
        super_new = super(UssdScreenType, mcls).__new__

        # is_abc = not any((b for b in bases if isinstance(b, UssdScreenType)))

        # raw_meta = dct.get('Meta')

        # meta_use_cls = raw_meta and getattr(raw_meta, '__metadata__', None)
        # meta_use_cls and dct.update(__metadata__=meta_use_cls)

        # Create class
        cls = super_new(mcls, name, bases, dct)

        # metadata_cls = get_metadata_class(cls, '__metadata__')
        # metadata_cls(cls, '_meta', raw_meta)

        # if not(is_abc or cls._meta.is_abstract):
        #     registry.set(cls._meta.name, cls)
        return cls

    # def __str__(cls):
    #     return cls._meta.name
    
    # def __repr__(cls):
    #     name = cls._meta.name
    #     return f'{cls.__module__}.{cls.__name__}({name=!r})'
    




class UssdPayload(UserString):
    
    __slots__ = ()

    # def __init__(self, data='', *, page_size=None, page_nav=None, foot_nav=None):
    #     super().__init__(data)
    #     self.page_size = page_size
    #     self.page_nav = page_nav
    #     self.foot_nav = foot_nav

    def extend(self, *objs, sep=' ', end='\n'):
        for o in objs:
            self.append(o, sep=sep, end=end)

    def append(self, *objs, sep=' ', end='\n'):
        self.data += f'{sep.join((str(s) for s in objs))}{end}'

    def prepend(self, *objs, sep=' ', end='\n'):
        self.data = f'{sep.join((str(s) for s in objs))}{end}{self.data}'.lstrip()

    def paginate(self, page_size, next_page_choice, prev_page_choice, foot=''):
        if isinstance(foot, (list, tuple)):
            foot_list = None #foot[:1]+[str(next_page_choice), ]+foot[1:]
            foot = '\n'.join(foot)
        else:
            foot_list = None

        foot = foot and '\n%s' % foot
        lfoot = len(foot)
        if len(self.data.strip()) + lfoot <= page_size:
            yield self.data.strip()+foot
        else:
            lnext, lprev = len(str(next_page_choice)) + \
                               len('\n'), len(str(prev_page_choice))
            lnav = lnext + lprev
            chunk, i = self.data.strip(), 0
            while chunk:
                lc = len(chunk)
                if i > 0 and lc <= lprev + page_size:
                    yield '%s\n%s' % (chunk, prev_page_choice)
                    chunk = None
                else:
                    yv = re.sub(r'([\n]+[^\n]+[\n]*)$', '', chunk[:(page_size -
                                lnav if i > 0 else page_size-lfoot-lnext)]).strip()
                    if i > 0:
                        yield '%s\n%s\n%s' % (yv, prev_page_choice, next_page_choice)
                    else:
                        if foot_list:
                            yield '%s\n%s' % (yv, '\n'.join(foot_list))
                        else:
                            yield '%s\n%s\n%s' % (yv, next_page_choice, foot)

                    chunk = chunk[len(yv)+1:].strip()
                i += 1

    def __str__(self):
        return self.data.strip()



class UssdScreen(t.Generic[T], metaclass=UssdScreenType):

    # META_OPTIONS_CLASS = ScreenMetaOptions

    CON = CON

    END = END

    init: t.ClassVar[t.Optional[t.Callable]] = None
    validate: t.ClassVar[t.Optional[t.Callable]] = None
    
    request: 'Request'
    app: 'FlexUssd' = property(attrgetter('request.app'))
    session: 'Session'= property(attrgetter('request.request'))


    _meta: t.ClassVar[ScreenMetaOptions]

    # lenargs = 1

    # class ERRORS:
    #     LEN_ARGS = 'Invalid Choice'
    #     INVALID_CHOICE = 'Invalid Choice'

    class Meta:
        # __metadata__ = ScreenMetaOptions
        state_class = ScreenState
        payload_class = UssdPayload


    nav_menu = dict([
        ('0', ("Previous", -1)),
        ('00', ("Home", 0)),
    ])

    class PaginationMenu(StrChoices):
        next = '99', 'More'
        prev = '0', 'Back'

        def __str__(self):
            return f'{self.value}: {self.label}'

    def __init__(self, state):
        self.state = state
        self.payload = self.create_payload()
    
    @property
    def print(self):
        return self.payload.append

    def create_payload(self):
        # return self._meta.payload_class()
        return UssdPayload('')

    def get_nav_menu_list(self):
        if not self.nav_menu:
            return []
        return list((('%s: %s' % (o, i[0])) for o, i in self.nav_menu.items()))
    
    # async def init(self, request: 'Request', inpt=None):
    #     pass
    
    async def render(self, request: 'Request'):
        raise NotImplementedError(f'{self.__class__.__name__}.render()')

    async def handle(self, request: 'Request', inpt):
        raise NotImplementedError(f'{self.__class__.__name__}.handle()')
    
    # async def validate(self, request: 'Request', inpt):
    #     return inpt
    
    async def handle_exception(self, request: 'Request', e, inpt=None):
        if inpt is not None and isinstance(e, exc.ValidationError):
            self.payload.prepend(e)
            return await self._async_render(request)
        else:
            raise e
    
    def _async_init(self, request: 'Request', inpt=None):
        return self.init(request, inpt)
    
    def _async_render(self, request: 'Request'):
        return self.render(request)

    def _async_handle(self, request: 'Request', inpt):
        return self.handle(request, inpt)
    
    def _async_validate(self, request: 'Request', inpt):
        return self.validate(request, inpt)
    
    def _async_handle_exception(self, request, e, inpt=None):
        return self.handle_exception(request, e, inpt)
    
    def abort(self, *args, **kwargs):
        raise exc.ValidationError(*args, **kwargs)
    
    async def __call__(self, request, inpt=None):
        rv, pages, i = None, self.state.get('_pages', []), 0
        self.request = request
            
        if inpt is not None and self.nav_menu and inpt in self.nav_menu:
            if self.state.get('_current_page', 0) == 0:
                return redirect(self.nav_menu[inpt][1])
                   
        pg_menu = self.PaginationMenu

        if inpt is not None and len(pages) > 1:
            if inpt in (pg_menu.next.value, pg_menu.prev.value):
                if inpt == pg_menu.prev.value and self.state.get('_current_page', 0) > 0:
                    self.state._current_page = i = self.state._current_page - 1
                    rv = self.state._action
                elif inpt == pg_menu.next.value and self.state.get('_current_page', 0) < len(pages)-1:
                    self.state._current_page = i = self.state._current_page + 1
                    rv = self.state._action
                rv and (inpt := None)

        if rv is None:
            try:
                if not self.state.get('__initialized__'):
                    if self.init is not None:
                        rv = await self._async_init(request, inpt)
                    self.state.__initialized__ = True
                    
                if rv is None and inpt is not None:
                    if self.validate is not None:
                        inpt = await self._async_validate(request, inpt)
                
                    if inpt is not None:
                        rv = await self._async_handle(request, inpt)
                rv is None and (rv := await self._async_render(request))
            except Exception as e:
                rv = await self._async_handle_exception(request, e, inpt)
            
            if rv == self.CON or rv == self.END:
                nav_menu = [] if rv == self.END else self.get_nav_menu_list()
                self.state._action = rv
                self.state._pages = pages = list(
                        self.payload.paginate(
                                ussd_settings.MAX_PAGE_LENGTH-4,
                                pg_menu.next, pg_menu.prev,
                                nav_menu
                            )
                        )
                self.state._current_page = i = 0
                # self.state._prev = self.payload
            else:
                return rv

        return rv, pages[i]
  