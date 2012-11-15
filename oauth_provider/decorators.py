from oauth2 import Error

try:
    from functools import update_wrapper
except ImportError:
    from django.utils.functional import update_wrapper  # Python 2.3, 2.4 fallback.

from django.utils.translation import ugettext as _

from oauth_provider.utils import initialize_server_request, send_oauth_error, get_oauth_request
from oauth_provider.consts import OAUTH_PARAMETERS_NAMES
from oauth_provider.store import store, InvalidTokenError

def oauth_required(view_func=None, resource_name=None):
    return CheckOAuth(view_func, resource_name)

class CheckOAuth(object):
    """
    Class that checks that the OAuth parameters passes the given test, raising
    an OAuth error otherwise. If the test is passed, the view function
    is invoked.

    We use a class here so that we can define __get__. This way, when a
    CheckOAuth object is used as a method decorator, the view function
    is properly bound to its instance.
    """
    def __init__(self, view_func, resource_name):
        self.view_func = view_func
        self.resource_name = resource_name
        update_wrapper(self, view_func)
        
    def __get__(self, obj, cls=None):
        view_func = self.view_func.__get__(obj, cls)
        return CheckOAuth(view_func, self.resource_name)
    
    def __call__(self, request, *args, **kwargs):
        if self.is_valid_request(request):
            oauth_request = get_oauth_request(request)
            consumer = store.get_consumer(request, oauth_request, 
                            oauth_request.get_parameter('oauth_consumer_key'))
            try:
                token = store.get_access_token(request, oauth_request, 
                                consumer, oauth_request.get_parameter('oauth_token'))
            except InvalidTokenError:
                return send_oauth_error(Error(_('Invalid access token: %s') % oauth_request.get_parameter('oauth_token')))
            try:
                parameters = self.validate_token(request, consumer, token)
            except Error, e:
                return send_oauth_error(e)
            
            if self.resource_name and token.resource.name != self.resource_name:
                return send_oauth_error(Error(_('You are not allowed to access this resource.')))
            elif consumer and token:
                return self.view_func(request, *args, **kwargs)
        
        return send_oauth_error(Error(_('Invalid request parameters.')))

    @staticmethod
    def is_valid_request(request):
        """
        Checks whether the required parameters are either in
        the http-authorization header sent by some clients,
        which is by the way the preferred method according to
        OAuth spec, but otherwise fall back to `GET` and `POST`.
        """
        is_in = lambda l: all((p in l) for p in OAUTH_PARAMETERS_NAMES)
        auth_params = request.META.get("HTTP_AUTHORIZATION", [])
        return is_in(auth_params) or is_in(request.REQUEST)

    @staticmethod
    def validate_token(request, consumer, token):
        oauth_server, oauth_request = initialize_server_request(request)
        return oauth_server.verify_request(oauth_request, consumer, token)
