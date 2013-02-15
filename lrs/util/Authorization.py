from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth import authenticate
from lrs.exceptions import Unauthorized, OauthUnauthorized, BadRequest, Forbidden
from lrs import models
import base64
from functools import wraps
import pdb

from oauth_provider.decorators import oauth_required
from oauth_provider.oauth.oauth import OAuthError
from django.utils.translation import ugettext as _
from oauth_provider.utils import initialize_server_request, send_oauth_error
from oauth_provider.consts import OAUTH_PARAMETERS_NAMES
from oauth_provider.consts import CONSUMER_STATES, ACCEPTED

# A decorator, that can be used to authenticate some requests at the site.
def auth(func):
    @wraps(func)
    def inner(request, *args, **kwargs):
        # Note: The cases involving OAUTH_ENABLED are here if OAUTH_ENABLED is switched from true to false
        # after a client has performed the handshake. (Not likely to happen, but could) 
        lrs_auth = request['lrs_auth']

        # There is an http lrs_auth request and http auth is enabled
        if lrs_auth == 'http' and settings.HTTP_AUTH_ENABLED:
            http_auth_helper(request)
        # There is an http lrs_auth request and http auth is not enabled
        elif lrs_auth == 'http' and not settings.HTTP_AUTH_ENABLED:
            raise BadRequest("HTTP authorization is not enabled. To enable, set the HTTP_AUTH_ENABLED flag to true in settings")
        # There is an oauth lrs_auth request and oauth is enabled
        elif lrs_auth == 'oauth' and settings.OAUTH_ENABLED: 
            oauth_helper(request)
        # There is an oauth lrs_auth request and oauth is not enabled
        elif lrs_auth == 'oauth' and not settings.OAUTH_ENABLED: 
            raise BadRequest("OAuth is not enabled. To enable, set the OAUTH_ENABLED flag to true in settings")
        # There is no lrs_auth request and there is some sort of auth enabled
        elif lrs_auth == 'none' and (settings.HTTP_AUTH_ENABLED or settings.OAUTH_ENABLED):
            raise Unauthorized("Auth is enabled but no authentication was sent with the request.")
        # There is no lrs_auth request and no auth is enabled
        elif lrs_auth == 'none' and not (settings.HTTP_AUTH_ENABLED or settings.OAUTH_ENABLED):
            request['auth'] = None
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
                    request['auth'] = user
                else:
                    raise Unauthorized("User is not authenticated: %s --- %s" % (uname,passwd))
    else:
        # The username/password combo was incorrect, or not provided.
        raise Unauthorized("Authorization header missing")

def oauth_helper(request):
    # Verifies the oauth request
    # if is_valid_request(request):
        # Validates the incoming consumer, token, and params
        # try:
        #     consumer, token, parameters = validate_token(request)
        # except OAuthError, e:
        #     raise OauthUnauthorized(send_oauth_error(e))
    pdb.set_trace()
    consumer = request['consumer']
    token = request['token']        
    if consumer and token:
        if consumer.status != ACCEPTED:
            raise OauthUnauthorized(send_oauth_error("%s has not been authorized" % str(consumer.name)))
        
        user = token.user
        user_name = user.username
        user_email = user.email
        consumer = token.consumer
        members = [
                    {
                        "account":{
                                    "name":consumer.key,
                                    "homePage":"/XAPI/OAuth/token/"
                        },
                        "objectType": "Agent"
                    },
                    {
                        "name":user_name,
                        "mbox":user_email,
                        "objectType": "Agent"
                    }
        ]
        kwargs = {"objectType":"Group", "member":members, "oauth_identifier":base64.b64encode("%s:%s" % (user.id, consumer.id))}
        oauth_group, created = models.group.objects.gen(**kwargs)
        request['auth'] = oauth_group
        request['oauth_token'] = token
    # else:
    #     raise OauthUnauthorized(send_oauth_error(OAuthError(_('Invalid request parameters.'))))

def is_valid_request(request):
    """
    Checks whether the required parameters are either in
    the http-authorization header sent by some clients,
    which is by the way the preferred method according to
    OAuth spec, but otherwise fall back to `GET` and `POST`.
    """
    is_in = lambda l: all((p in l) for p in OAUTH_PARAMETERS_NAMES)
    auth_params = request.get("Authorization", [])
    return is_in(auth_params)

def validate_token(request):
    # Creates the oauth server and request. Verifies the request against server
    oauth_server, oauth_request = initialize_server_request(request)
    return oauth_server.verify_request(oauth_request)