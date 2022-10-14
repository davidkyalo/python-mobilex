import asyncio
import typing as t







class SyncRenderMixin:
    """SyncRenderMixin doc"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        m = getattr(cls, 'render', None)
        assert not(m and asyncio.iscoroutinefunction(m)), (
            f'{cls.__module__}.{cls.__name__}.render() cannot be async '
            f'for SyncRenderMixin subclasses'
        )

    async def _async_render(self, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.render, *args)

    

class SyncHandleMixin:
    """SyncRenderMixin doc"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        m = getattr(cls, 'handle', None)
        assert not(m and asyncio.iscoroutinefunction(m)), (
            f'{cls.__module__}.{cls.__name__}.handle() cannot be async '
            f'for SyncHandleMixin subclasses'
        )

    async def _async_handle(self, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.handle, *args)

        

class SyncValidateMixin:
    """SyncRenderMixin doc"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        m = getattr(cls, 'validate', None)
        assert not(m and asyncio.iscoroutinefunction(m)), (
            f'{cls.__module__}.{cls.__name__}.validate() cannot be async '
            f'for SyncHandleMixin subclasses'
        )

    async def _async_validate(self, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.validate, *args)

    

class SyncHandleExceptionMixin:
    """SyncHandleExceptionMixin doc"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        m = getattr(cls, 'handle_exception', None)
        assert not(m and asyncio.iscoroutinefunction(m)), (
            f'{cls.__module__}.{cls.__name__}.handle_exception() cannot be async '
            f'for SyncHandleMixin subclasses'
        )

    async def _async_handle_exception(self, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.handle_exception, *args)

    

class SyncMixin(SyncRenderMixin, SyncHandleMixin, 
                SyncValidateMixin, SyncHandleExceptionMixin):
    """SyncMixin doc"""


