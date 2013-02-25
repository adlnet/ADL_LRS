from oauth.oauth import OAuthError

try:
    from functools import wraps, update_wrapper
except ImportError:
    from django.utils.functional import wraps, update_wrapper  # Python 2.3, 2.4 fallback.

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.translation import ugettext as _

from utils import initialize_server_request, send_oauth_error
from consts import OAUTH_PARAMETERS_NAMES

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
        self.request = request
        self.view_func = view_func
        # lou w - name scope instead of resource
        self.scopes = resource_name
        update_wrapper(self, request)
        
    def __get__(self, obj, cls=None):
        return CheckOAuth(request)
    
    def __call__(self, request):
        if self.is_valid_request(request):
            try:
                consumer, token, parameters = self.validate_token(request)
            except OAuthError, e:
                return send_oauth_error(e)

            # lou w - changed to check token scope and self scope instead of resource
            if self.scopes and token.scope != self.scopes:
                return send_oauth_error(OAuthError(_('You are not allowed to access this resource.')))
            elif consumer and token:
                return self.view_func(request, *args, **kwargs)
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
        # lou w = all auth params will be in Authorization or HTTP_AUTHORIZATION
        auth_params = request.META.get("HTTP_AUTHORIZATION", request.META.get("Authorization", []))
        return is_in(auth_params) or is_in(request.REQUEST)

    @staticmethod
    def validate_token(request):
        oauth_server, oauth_request = initialize_server_request(request)
        return oauth_server.verify_request(oauth_request)
