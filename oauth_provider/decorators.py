import oauth2 as oauth

try:
    from functools import update_wrapper
except ImportError:
    from django.utils.functional import update_wrapper  # Python 2.3, 2.4 fallback.

from django.utils.translation import ugettext as _

from responses import INVALID_PARAMS_RESPONSE, INVALID_CONSUMER_RESPONSE, COULD_NOT_VERIFY_OAUTH_REQUEST_RESPONSE, INVALID_SCOPE_RESPONSE
from utils import initialize_server_request, send_oauth_error, get_oauth_request, verify_oauth_request
from consts import OAUTH_PARAMETERS_NAMES
from store import store, InvalidTokenError, InvalidConsumerError
from functools import wraps


class CheckOauth(object):
    """
    Decorator that checks that the OAuth parameters passes the given test, raising
    an OAuth error otherwise. If the test is passed, the view function
    is invoked.

    We use a class here so that we can define __get__. This way, when a
    CheckOAuth object is used as a method decorator, the view function
    is properly bound to its instance.
    """
    def __init__(self, scope_name=None):
        self.scope_name = scope_name

    def __new__(cls, arg=None):
        if not callable(arg):
            return super(CheckOauth, cls).__new__(cls)
        else:
            obj =  super(CheckOauth, cls).__new__(cls)
            obj.__init__()
            return obj(arg)

    def __call__(self, view_func):

        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            oauth_request = get_oauth_request(request)
            if oauth_request is None:
                return INVALID_PARAMS_RESPONSE

            try:
                consumer = store.get_consumer(request, oauth_request, oauth_request['oauth_consumer_key'])
            except InvalidConsumerError:
                return INVALID_CONSUMER_RESPONSE

            try:
                token = store.get_access_token(request, oauth_request, consumer, oauth_request.get_parameter('oauth_token'))
            except InvalidTokenError:
                return send_oauth_error(oauth.Error(_('Invalid access token: %s') % oauth_request.get_parameter('oauth_token')))

            if not verify_oauth_request(request, oauth_request, consumer, token):
                return COULD_NOT_VERIFY_OAUTH_REQUEST_RESPONSE

            # LRS CHANGE - SCOPE IS JUST A CHARFIELD NOW - JUST COMPARE THE VALUES
            if self.scope_name and (not token.scope
                                    or token.scope != self.scope_name):
                return INVALID_SCOPE_RESPONSE

            # if self.scope_name and (not token.scope
            #                         or token.scope.name != self.scope_name):
            #     return INVALID_SCOPE_RESPONSE

            if token.user:
                request.user = token.user
            return view_func(request, *args, **kwargs)

        return wrapped_view

    # LRS CHANGE - ADDED FUNCTION SO LRS CAN VALIDATE ACCESS TOKEN ONCE USER IS THROUGH OAUTH PROCESS
    # AND TRIES ACCESS RESOURCES
    def check_access_token(self, request):
        oauth_request = get_oauth_request(request)
        if oauth_request is None:
            return oauth.Error(_('Invalid request parameters.'))

        try:
            consumer = store.get_consumer(request, oauth_request, oauth_request['oauth_consumer_key'])
        except InvalidConsumerError:
            raise INVALID_CONSUMER_RESPONSE

        try:
            token = store.get_access_token(request, oauth_request, consumer, oauth_request.get_parameter('oauth_token'))
        except InvalidTokenError:
            raise oauth.Error(_('Invalid access token: %s') % oauth_request.get_parameter('oauth_token'))

        if not verify_oauth_request(request, oauth_request, consumer, token):
            raise oauth.Error(_('Could not verify OAuth request.'))

        # LRS CHANGE - SCOPE IS JUST A CHARFIELD NOW - JUST COMPARE THE VALUES
        if self.scope_name and (not token.scope
                                or token.scope != self.scope_name):
            raise oauth.Error(_('You are not allowed to access this resource.'))

        # if self.scope_name and (not token.scope
        #                         or token.scope.name != self.scope_name):
        #     return INVALID_SCOPE_RESPONSE

        if token.user:
            request.user = token.user      

oauth_required = CheckOauth