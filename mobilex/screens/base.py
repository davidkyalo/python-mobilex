from inspect import isawaitable
from operator import attrgetter
import re
import typing as t
from collections import UserString, abc
from logging import getLogger


from ..utils.types import NamespaceDict, FrozenNamespaceDict
from ..utils.enums import StrChoices


from ..response import redirect
from .. import exc


if t.TYPE_CHECKING:
    from mobilex import Request, Response, App
    from mobilex.sessions import Session


logger = getLogger(__name__)


NOTHING = object()


T = t.TypeVar("T")

CON = "CON"

END = "END"


class ScreenMetaOptions:
    pass


class ScreenState(NamespaceDict):
    __slots__ = ()

    def __init__(self, screen, *bases, **data):
        super().__init__(*bases, **data)
        self.screen = screen

    def reset(self, *keep, **values):
        ("screen" in keep) or values.setdefault("screen", self.screen)
        for k in keep:
            if k in self:
                values.setdefault(k, getattr(self, k))
        self.clear()
        self.update(values)


class ScreenType(type):
    def __new__(mcls, name, bases, dct):
        from .mixins import SyncRenderMixin, SyncHandleMixin

        super_new = super(ScreenType, mcls).__new__

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

    def extend(self, *objs, sep=" ", end="\n"):
        for o in objs:
            self.append(o, sep=sep, end=end)

    def append(self, *objs, sep=" ", end="\n"):
        self.data += f"{sep.join((str(s) for s in objs))}{end}"

    def prepend(self, *objs, sep=" ", end="\n"):
        self.data = f"{sep.join((str(s) for s in objs))}{end}{self.data}".lstrip()

    def paginate(self, page_size, next_page_choice, prev_page_choice, foot=""):
        if isinstance(foot, (list, tuple)):
            foot_list = None  # foot[:1]+[str(next_page_choice), ]+foot[1:]
            foot = "\n".join(foot)
        else:
            foot_list = None

        foot = foot and "\n%s" % foot
        lfoot = len(foot)
        if len(self.data.strip()) + lfoot <= page_size:
            yield self.data.strip() + foot
        else:
            lnext, lprev = len(str(next_page_choice)) + len("\n"), len(
                str(prev_page_choice)
            )
            lnav = lnext + lprev
            chunk, i = self.data.strip(), 0
            while chunk:
                lc = len(chunk)
                if i > 0 and lc <= lprev + page_size:
                    yield "%s\n%s" % (chunk, prev_page_choice)
                    chunk = None
                else:
                    yv = re.sub(
                        r"([\n]+[^\n]+[\n]*)$",
                        "",
                        chunk[
                            : (page_size - lnav if i > 0 else page_size - lfoot - lnext)
                        ],
                    ).strip()
                    if i > 0:
                        yield "%s\n%s\n%s" % (yv, prev_page_choice, next_page_choice)
                    else:
                        if foot_list:
                            yield "%s\n%s" % (yv, "\n".join(foot_list))
                        else:
                            yield "%s\n%s\n%s" % (yv, next_page_choice, foot)

                    chunk = chunk[len(yv) + 1 :].strip()
                i += 1

    def __str__(self):
        return self.data.strip()


class Action(t.NamedTuple):
    key: str
    label: str
    handler: str | abc.Callable = None
    screen: str | int = None
    context: abc.Mapping = None

    def handle(self, screen: "Screen", value: str):
        ctx = self.context or {}
        if (to := self.screen) is not None:
            return redirect(to, **ctx)
        elif callable(func := self.handler):
            return func(screen, value, **ctx)
        elif isinstance(func, str):
            return getattr(screen, func)(value, **ctx)

    def __str__(self) -> str:
        return f"{self.key}"


class Screen(t.Generic[T], metaclass=ScreenType):
    # META_OPTIONS_CLASS = ScreenMetaOptions

    CON = CON

    END = END

    exit_code = CON

    init: t.ClassVar[t.Optional[t.Callable]] = None
    validate: t.ClassVar[t.Optional[t.Callable]] = None

    request: "Request"
    app: "App" = property(attrgetter("request.app"))
    session: "Session" = property(attrgetter("request.session"))
    state: ScreenState

    _meta: t.ClassVar[ScreenMetaOptions]

    # lenargs = 1

    # class ERRORS:
    #     LEN_ARGS = 'Invalid Choice'
    #     INVALID_CHOICE = 'Invalid Choice'

    class Meta:
        # __metadata__ = ScreenMetaOptions
        state_class = ScreenState
        payload_class = UssdPayload

    # nav_menu = dict(
    #     [
    #         ("0", ("Back", -1)),
    #         ("00", ("Home", 0)),
    #     ]
    # )

    actions = [
        Action("0", "Back", screen=-1),
        Action("00", "Home", screen=0),
    ]

    class PaginationMenu(StrChoices):
        next = "99", "More"
        prev = "0", "Back"

        def __str__(self):
            return f"{self.value:<2} {self.label}"

    def __init__(self, state):
        self.state = state
        self.payload = self.create_payload()

    @t.overload
    def print(self, *objs, sep=" ", end="\n"):
        ...

    @property
    def print(self):
        return self.payload.append

    @property
    def _cached_actions(self) -> list[Action]:
        try:
            return self.__dict__["_cached_actions"]
        except KeyError:
            return self.__dict__.setdefault("_cached_actions", self.get_actions())

    def create_payload(self):
        # return self._meta.payload_class()
        return UssdPayload("")

    def get_actions(self) -> list[Action]:
        return self.actions or []

    def get_action_dict(self):
        return {str(act.key): act for act in self._cached_actions}

    def render_action_list(self):
        return [f"{act.key:<2} {act.label}" for act in self._cached_actions]

    async def handle(self, inpt):
        if self.get_action_dict():
            self.print("Invalid choice!")

    async def render(self):
        return

    # async def validate(self, request: 'Request', inpt):
    #     return inpt

    async def handle_exception(self, e, inpt=None):
        if inpt is not None and isinstance(e, exc.ValidationError):
            self.payload.prepend(e)
            return await self._async_render()
        else:
            raise e

    async def _async_init(self, inpt=None):
        rv = self.init(inpt)
        if isawaitable(rv):
            rv = await rv
        return rv

    async def _async_render(self):
        rv = self.render()
        if isawaitable(rv):
            rv = await rv
        return rv

    async def _async_handle(self, inpt):
        rv = self.handle(inpt)
        if isawaitable(rv):
            rv = await rv
        return rv

    async def _async_validate(self, inpt):
        rv = self.validate(inpt)
        if isawaitable(rv):
            rv = await rv
        return rv

    async def _async_handle_exception(self, e, inpt=None):
        rv = self.handle_exception(e, inpt)
        if isawaitable(rv):
            rv = await rv
        return rv

    def abort(self, *args, **kwargs):
        raise exc.ValidationError(*args, **kwargs)

    async def __call__(self, request: "Request", input=None):
        self.request = request
        rv, pages, i = None, self.state.get("_pages", []), 0
        current_page = self.state.get("_current_page", 0)
        actions = self.get_action_dict()
        key = input if input is None else f"{input}".strip()
        if current_page == 0 and key is not None and key in actions:
            if (rv := actions[key].handle(self, key)) is not None:
                return rv
            input = key = None

        pg_menu = self.PaginationMenu

        if key is not None and len(pages) > 1:
            if key in (pg_menu.next.value, pg_menu.prev.value):
                if key == pg_menu.prev.value and current_page > 0:
                    self.state._current_page = i = current_page - 1
                    rv = self.state._action
                elif key == pg_menu.next.value and current_page < len(pages) - 1:
                    self.state._current_page = i = current_page + 1
                    rv = self.state._action
        if rv is None:
            try:
                if not self.state.get("__initialized__"):
                    if self.init is not None:
                        rv = await self._async_init(input)
                    self.state.__initialized__ = True

                if rv is None and input is not None:
                    if self.validate is not None:
                        input = await self._async_validate(input)

                    if input is not None:
                        rv = await self._async_handle(input)
                rv is None and (rv := await self._async_render())
            except Exception as e:
                rv = await self._async_handle_exception(e, input)

            if rv is None:
                rv = self.exit_code

            if rv == self.CON or rv == self.END:
                nav_menu = [] if rv == self.END else self.render_action_list()
                self.state._action = rv
                self.state._pages = pages = list(
                    self.payload.paginate(
                        request.app.config.max_page_length - 4,
                        pg_menu.next,
                        pg_menu.prev,
                        nav_menu,
                    )
                )
                self.state._current_page = i = 0
                # self.state._prev = self.payload
            else:
                return rv

        return rv, pages[i]
