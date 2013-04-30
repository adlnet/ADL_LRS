import base64
from functools import wraps
from django.conf import settings
from django.contrib.auth import authenticate
from lrs.exceptions import Unauthorized, OauthUnauthorized, BadRequest
from lrs.models import Token, agent
from oauth_provider.utils import send_oauth_error
from oauth_provider.consts import  ACCEPTED
import pdb

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
    consumer = request['oauth_consumer']
    token = request['oauth_token']
    
    # Make sure consumer has been accepted by system
    if consumer.status != ACCEPTED:
        raise OauthUnauthorized(send_oauth_error("%s has not been authorized" % str(consumer.name)))

    # make sure the token is an approved access token
    if token.token_type != Token.ACCESS or not token.is_approved:
        raise OauthUnauthorized(send_oauth_error("The token is not valid"))
    
    user = token.user
    user_name = user.username
    if user.email.startswith('mailto:'):
        user_email = user.email
    else:
        user_email = 'mailto:%s' % user.email
    consumer = token.consumer                
    members = [
                {
                    "account":{
                                "name":consumer.key,
                                "homePage":"/XAPI/OAuth/token/"
                    },
                    "objectType": "Agent",
                    "oauth_identifier": "anonoauth:%s" % (consumer.key)
                },
                {
                    "name":user_name,
                    "mbox":user_email,
                    "objectType": "Agent"
                }
    ]
    kwargs = {"objectType":"Group", "member":members,"oauth_identifier": "anongroup:%s-%s" % (consumer.key, user_email)}
    # create/get oauth group and set in dictionary
    # oauth_group, created = agent.objects.gen(**kwargs)
    oauth_group, created = agent.objects.oauth_group(**kwargs)
    request['auth'] = oauth_group
