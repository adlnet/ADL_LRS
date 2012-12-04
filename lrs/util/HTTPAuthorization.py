from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth import authenticate
from lrs.exceptions import Unauthorized, OauthUnauthorized
from lrs import models
import base64
from functools import wraps
import pdb

from oauth_provider.decorators import oauth_required
from oauth_provider.oauth.oauth import OAuthError
from django.utils.translation import ugettext as _
from oauth_provider.utils import initialize_server_request, send_oauth_error
from oauth_provider.consts import OAUTH_PARAMETERS_NAMES



def http_auth(func):
    """
    A decorator, that can be used to authenticate some requests at the site.
    """
    @wraps(func)
    def inner(request, *args, **kwargs):
        if settings.HTTP_AUTH or settings.OAUTH:
            if request['lrs_auth'] == 'http':
                http_auth_helper(request)
            else:
                oauth_helper(request)

        return func(request, *args, **kwargs)
    return inner

def http_auth_helper(request):
    if request.has_key('Authorization'):
        auth = request['Authorization'].split()
        if len(auth) == 2:
            if auth[0].lower() == 'basic':
                # Currently, only basic http auth is used.
                uname, passwd = base64.b64decode(auth[1]).split(':')
                user = authenticate(username=uname, password=passwd)
                if user:
                    # If the user successfully logged in, then add/overwrite
                    # the user object of this request.
                    request['user'] = user
    else:
        # The username/password combo was incorrect, or not provided.
        raise Unauthorized("Unauthorized")

    
def oauth_helper(request):
    if is_valid_request(request):
        try:
            consumer, token, parameters = validate_token(request)
        except OAuthError, e:
            raise OauthUnauthorized(send_oauth_error(e))

        if consumer and token:
            request['user'] = token.user
    else:
        raise OauthUnauthorized(send_oauth_error(OAuthError(_('Invalid request parameters.'))))

def is_valid_request(request):
    """
    Checks whether the required parameters are either in
    the http-authorization header sent by some clients,
    which is by the way the preferred method according to
    OAuth spec, but otherwise fall back to `GET` and `POST`.
    """
    is_in = lambda l: all((p in l) for p in OAUTH_PARAMETERS_NAMES)
    auth_params = request.get("HTTP_AUTHORIZATION", [])
    auth_params_1 = request.get("Authorization", [])
    return is_in(auth_params) or is_in(auth_params_1)

def validate_token(request):
    oauth_server, oauth_request = initialize_server_request(request)
    return oauth_server.verify_request(oauth_request)