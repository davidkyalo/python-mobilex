
class UssdError(Exception):

    __slots__ = ('messages', 'code', '__weakref__',)

    default_code = 'error'
    default_message = 'Error'

    def __init__(self, *msgs, code=None):
        self.messages = msgs and list(msgs) or [self.default_message,]
        self.code = self.default_code if code is None else code

    @property
    def message(self):
        return '\n'.join(self)
    
    def __iter__(self):
        return iter((str(m) for m in self.messages))

    def __str__(self):
        return self.message

    def __repr__(self):
        return f'{type(self).__name__}({", ".join(map(repr, self))})'



class ValidationError(UssdError):
    
    default_code = 'invalid'
    default_message = 'Error! Invalid input'




class InputError(ValidationError):
    pass



class InvalidChoiceError(ValidationError):

    default_code = 'invalid_choice'
    default_message = 'Error! Invalid choice'


