import typing as t


from collections import ChainMap

from .const import ResponseType


if t.TYPE_CHECKING:
    from . import Request

class _ResponseMeta(type):
    
    def __new__(mcls, name, bases, dct):
        super_new = super(_ResponseMeta, mcls).__new__

        st = dct['__state_attrs__'] = set(dct.get('__state_attrs__', ()))
        exclude = {n for n in st if n[0] == '-'}
        st -= exclude
        st.update(*(b.__state_attrs__ for b in bases if isinstance(b, _ResponseMeta)))
        st -= {n[1:] for n in exclude}
        # Create class
        return super_new(mcls, name, bases, dct)



class Response(metaclass=_ResponseMeta):
    """USSD response object"""

    type: ResponseType = None
    request: 'Request' = None
    content: t.Any
    ctx: t.Mapping

    __state_attrs__ = 'type', 'content', 'ctx'

    def __init__(self, content: t.Optional[t.Any] = None, 
                ctx: t.Optional[t.Mapping] = None, 
                /, type: t.Optional[ResponseType] = None):

        self.content = content
        self.type = type or self.__class__.type
        self.ctx = ChainMap() if ctx is None else ChainMap({}, ctx)
    
    def get_context(self, request, ctx: t.Optional[t.Mapping] = None):
        return self.ctx.new(ctx)

    async def render_content(self, request, ctx: t.Optional[t.Mapping] = None):
        return f'{self.type} {self.content}'

    def __getstate__(self):
        return {n: getattr(self, n) for n in self.__state_attrs__}
        
    def __setstate__(self, state):
        for k,v in state.items():
            setattr(self, k, v)

    async def __call__(self, request, ctx: t.Optional[t.Mapping] = None):
        return await self.render_content(request, ctx)



R_to = t.TypeVar('R_to', str, int)
class RedirectResponse(t.Generic[R_to], Response):

    __state_attrs__ = 'to',

    type: ResponseType = ResponseType.PUSH

    def __init__(self, to: R_to, 
                inpt: t.Optional[t.Any] = None, 
                ctx: t.Optional[t.Mapping] = None, /, 
                type: t.Optional[ResponseType] = None):
        super().__init__(inpt, ctx, type=type)
        self.to = to if isinstance(to, (str, int)) else str(to)




class RedirectBackResponse(RedirectResponse[int]):

    type: ResponseType = ResponseType.POP




def redirect(to: R_to, inpt: t.Optional[t.Any] = None, /, **ctx) -> RedirectResponse[R_to]:
    if isinstance(to, int):
        return RedirectBackResponse(to, inpt, ctx)
    else:
        return RedirectResponse(to, inpt, ctx)

