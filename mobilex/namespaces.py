

_module_namespace_registry = dict()


def ussd_namespace(module_name, name=None):
    """Register USSD namespace for given module.

    This is used to namespace USSD resources such as USSD Screens.
    For example::
        ussd_namespace(__name__, 'foo')

        class ScreenBar(UssdScreen):
            class Meta:
                id = '.bar'

        # Will result to
        ScreenBar._meta.id == 'foo.bar'


    Args:
        module_name: The module's name. Usually the __name__ module variable.
        name: The namespace. If omitted, the module_name is used. If it
            starts with a '.' (dot), it is prefixed with the nearest ancestor's
            namespace name or raise an error if ancestor not available.
    """
    if not module_name or not isinstance(module_name, str):
        raise ValueError(
            'Arg module_name must be a valid module name string. %s given'\
            % ('Empty str' if module_name == '' else type(module_name),)
        )

    name = name or module_name

    if name[0] == '.':
        try:
            name = get_ussd_namespace(module_name.rsplit('.', 1)[0]) + name
        except UssdNamespaceError as e:
            raise UssdNamespaceError(
                'Relatively named ussd namespace %s in %s has no registered '\
                'ancestor.' % (name, module_name)
            ) from e

    if name[-1] == '.':
        raise ValueError(
            'Error registering namespace "%s". USSD namespaces '\
            'cannot end with a \'.\' (dot).' % (name,)
        )
    elif module_name in _module_namespace_registry:
        if _module_namespace_registry[module_name] != name:
            raise RuntimeError(
                'Duplicate USSD namespace on module %s.' % (module_name,)
            )
    else:
        _module_namespace_registry[module_name] = name
        return name



def get_ussd_namespace(module_name, silent=False):
    if not module_name or not isinstance(module_name, str):
        raise ValueError(
            'Arg module_name must be a none empty string. %s given'\
            % ('Empty str' if module_name == '' else type(module_name),)
        )

    if module_name in _module_namespace_registry:
        return _module_namespace_registry[module_name]
    else:
        parts = module_name.split('.')
        for i in range(1,len(parts)):
            key = '.'.join(parts[:i*-1])
            if key in _module_namespace_registry:
                return _module_namespace_registry[key]

    if not silent:
        raise UssdNamespaceError(
            '%s is not in a registered namespace' % module_name
        )




class UssdNamespaceError(Exception):
    """Invalid namespace."""
    pass
