
import typing as t



from mobilex.screens import UssdScreen
from mobilex.router import UssdRouter
from mobilex.response import redirect




router = UssdRouter('example')


@router.start_screen('initial')
class InitialScreen(UssdScreen):

    async def render(self, request):
        return redirect('.home')
        
        




@router.screen('not_allowed')
class AnonymousUserScreen(UssdScreen):

    async def render(self, request):
        self.print(f"You are not welcome here.")
        return self.END
    
    

    
@router.screen('home')
class HomeScreen(UssdScreen):

    async def handle(self, request: 'Request', inpt):
        self.print(f'Your input was; {inpt!r}')

    async def render(self, request):
        self.print(f"Welcome home dear user.")
        return self.END
    