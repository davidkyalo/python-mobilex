import time
import datetime


from .utils.local import PromiseProxy

from .settings import ussd_settings
from .sessions import SessionKey, Session

_epoch = datetime.datetime(2017, 1, 1).timestamp()




class CacheBackend(object):

    session_class = Session
    key_class = SessionKey

    def __init__(self, app=None):
        pass

    def get_session_key_class(self, request):
        return self.key_class

    def get_session_class(self, request):
        return self.session_class

    def get_session_timeout(self):
        return ussd_settings.SESSION_TIMEOUT

    # def get_screen_state_timeout(self):
    # 	return ussd_settings.SCREEN_STATE_TIMEOUT

    def get_request_sid(self, request):
        rv = request.ussd_data.get('session_id')
        if not rv:
            rv = int((time.time() - _epoch) * 1000000)
        return rv

    def get_request_uid(self, request):
        return request.ussd_data.get('phone_number', '0')

    def get_session_key(self, request):
        cls = self.get_session_key_class(request)
        return cls(uid=self.get_request_uid(request), sid=self.get_request_sid(request))

    # def get_screen_state_key(self, session):
    # 	return '%s/screen-state' % (session.key,)

    def create_new_session(self, key, request):
        cls = self.get_session_class(request)
        return cls(key)

    def get_saved_session(self, key, request):
        return cache.get(key.uid)

    def save_session(self, session, request):
        return cache.set(str(session.key.uid), session, self.get_session_timeout())

    def open_session(self, req):
        key = self.get_session_key(req)
        session = self.get_saved_session(key, req) or self.create_new_session(key, req)
        if session.key != key:
            session.restored = session.key
            session.key = key
        # session.key = key
        session.start_request(req)
        return session

    def close_session(self, session, request, response):
        session.finish_request(request)
        self.save_session(session, request)

    # def get_saved_screen_state(self, session):
    # 	return cache.get(self.get_screen_state_key(session))

    # def save_screen_state(self, state, session):
    # 	cache.set(self.get_screen_state_key(session), state, self.get_screen_state_timeout())

    # def expire_screen_state(self, session):
    # 	cache.delete(self.get_screen_state_key(session))


def _get_ussd_session_backend():
    cls = ussd_settings.SESSION_BACKEND
    return cls()


ussd_session_backend = PromiseProxy[CacheBackend](_get_ussd_session_backend)