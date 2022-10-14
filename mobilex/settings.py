"""
Settings for USSD are all namespaced in the USSD setting.
For example your project's `settings.py` file might look like this:

USSD = {
    ...
}

This module provides the `ussd_setting` object, that is used to access USSD
settings, checking for user settings first, then falling back to the defaults.
"""
from types import SimpleNamespace
import six
from importlib import import_module



_USER_SETTINGS_KEY = 'USSD'


DEFAULTS = dict(
    # SESSION_BACKEND = 'flex.ussd.sessions.SessionManager',
    SESSION_MANAGER = 'flex.ussd.sessions.SessionManager',
    SESSION_KEY_PREFIX = 'ussd_session',
    SESSION_TIMEOUT = 30,
    URLS = (),
    DEFAULT_HTTP_METHODS = 'GET',
    START_SCREEN = None,
    HOME_SCREEN = None,
    SCREEN_STATE_LIFETIMES = 60,
    MAX_PAGE_LENGTH=182,
    # SCREEN_UID_LEN=2,
    # HISTORY_STATE_X = 16
)


# List of settings that may be in string import notation.
IMPORT_STRINGS = (
    'SESSION_MANAGER',
)


VALUE_PARSERS = dict(
    URLS = lambda v: normalize_urls(v),
    DEFAULT_HTTP_METHODS = lambda v: ensure_list(v, str_split=True)
)


VALUE_CHECKS = dict(
    START_SCREEN = lambda v: v is not None,
    SCREEN_STATE_LIFETIMES = lambda v: v >= 2
)


# List of settings that have been removed
REMOVED_SETTINGS = (
#
)


def ensure_list(val, str_split=None):
    if str_split is not None and isinstance(val, str):
        if str_split == True:
            return val.split()
        else:
            return val.split(str_split)

    if not isinstance(val, (tuple, list)):
        return [val]
    else:
        return list(val)


def normalize_urls(urls):
    if not isinstance(urls, (tuple, list)):
        raise ValueError(
            'USSD.URLS setting value must be a list or tuple. %s given.'\
            % type(urls))

    defaults = dict(path=None, methods=ussd_settings.DEFAULT_HTTP_METHODS)
    rv = []

    for url in urls:
        if isinstance(url, str):
            url = dict(path=url)

        if not isinstance(url, dict):
            raise ValueError(
                'Items of USSD.URLS setting must be str or dict. %s given.'\
                % type(url)
            )

        for k,v in defaults.items():
            url.setdefault(k, v)

        if not url['path'] or not isinstance(url['path'], str):
            raise ValueError(
                'USSD.URLS[][\'path\'] setting must be str (regex pattern). %s given.'\
                % type(url['path'])
            )

        url['methods'] = ensure_list(url['methods'], str_split=True)

        rv.append(url)
    return rv



def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if val is None:
        return None
    elif isinstance(val, six.string_types):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    try:
        # Nod to tastypie's use of importlib.
        parts = val.split('.')
        module_path, class_name = '.'.join(parts[:-1]), parts[-1]
        module = import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        msg = "Could not import '%s' for USSD setting '%s'. %s: %s." % (val, setting_name, e.__class__.__name__, e)
        raise ImportError(msg)


class UssdSettings(object):
    """
    A settings object, that allows USDD settings to be accessed as properties.
    For example:

        from flex.ussd.settings import ussd_settings
        print(ussd_settings.SESSION_KEY_PREFIX)

    Any setting with string import paths will be automatically resolved
    and return the object, rather than the string literal.
    """
    
    _base_settings = SimpleNamespace()

    def __init__(self, user_settings=None, defaults=None, import_strings=None, value_parsers=None, value_checks=None):
        if user_settings:
            self._user_settings = self.__check_user_settings(user_settings)
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS
        self.value_parsers = value_parsers or VALUE_PARSERS
        self.value_checks = value_checks or VALUE_CHECKS

    @property
    def user_settings(self):
        if not hasattr(self, '_user_settings'):
            self._user_settings = getattr(self._base_settings, _USER_SETTINGS_KEY, {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError("Invalid USSD setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        if attr in self.value_parsers:
            val = self.value_parsers[attr](val)

        if attr in self.value_checks and not self.value_checks[attr](val):
            raise ValueError('Invalid value for USSD setting: %s, value %s' % (attr, val))

        # Coerce import strings into classes
        if attr in self.import_strings:
            val = perform_import(val, attr)

        # Cache the result
        setattr(self, attr, val)
        return val

    def __check_user_settings(self, user_settings):
        for setting in REMOVED_SETTINGS:
            if setting in user_settings:
                raise RuntimeError("The '%s' setting has been removed. Please refer to the docs for available settings." % setting)
        return user_settings


ussd_settings = UssdSettings(None, DEFAULTS, IMPORT_STRINGS, VALUE_PARSERS, VALUE_CHECKS)


