

from enum import Enum





class ResponseType(str, Enum):
    """USSD response types

    Attributes:
        CON     Continue response
        END     End the session
        POP     Pop the state
        PUSH    Push the request to another screen
    """

    CON = 'CON'
    END = 'END'
    POP = 'POP'
    PUSH = 'PUSH'

