from oauth.oauth import OAuthError

try:
    from functools import wraps, update_wrapper
except ImportError:
    from django.utils.functional import wraps, update_wrapper  # Python 2.3, 2.4 fallback.

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.translation import ugettext as _

from utils import initialize_server_request, send_oauth_error
from consts import OAUTH_PARAMETERS_NAMES
import pdb
def oauth_required(request):
    return CheckOAuth.handle_request(request)

class CheckOAuth(object):
    """
    Class that checks that the OAuth parameters passes the given test, raising
    an OAuth error otherwise. If the test is passed, the view function
    is invoked.

    We use a class here so that we can define __get__. This way, when a
    CheckOAuth object is used as a method decorator, the view function
    is properly bound to its instance.
    """
    def __init__(self, request):
        # pdb.set_trace()
        self.request = request
        self.view_func = view_func
        self.resource_name = resource_name
        update_wrapper(self, request)
        
    def __get__(self, obj, cls=None):
        return CheckOAuth(request)
    
    def __call__(self, request):
        pdb.set_trace()
        if self.is_valid_request(request):
            try:
                consumer, token, parameters = self.validate_token(request)
            except OAuthError, e:
                return send_oauth_error(e)

            # Not sure how self.resource_name was being passed...the model class should handle this later 
            # if self.resource_name and token.resource.name != self.resource_name:
            #     return send_oauth_error(OAuthError(_('You are not allowed to access this resource.')))
            # elif consumer and token:
            #     return self.view_func(request, *args, **kwargs)
            if consumer and token:
                request['user'] = token.user
        else:
            return send_oauth_error(OAuthError(_('Invalid request parameters.')))
    @staticmethod
    def handle_request(self, request):
        # pdb.set_trace()
        if self.is_valid_request(request):
            try:
                consumer, token, parameters = self.validate_token(request)
            except OAuthError, e:
                return send_oauth_error(e)

            if consumer and token:
                request['user'] = token.user
        else:
            return send_oauth_error(OAuthError(_('Invalid request parameters.')))



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
        auth_params_1 = request.META.get("Authorization", [])
        return is_in(auth_params) or is_in(request.REQUEST) or is_in(auth_params_1)

    @staticmethod
    def validate_token(request):
        oauth_server, oauth_request = initialize_server_request(request)
        return oauth_server.verify_request(oauth_request)
