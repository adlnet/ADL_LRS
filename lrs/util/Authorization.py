import base64
from functools import wraps
from django.conf import settings
from django.contrib.auth import authenticate
from lrs.exceptions import Unauthorized, OauthUnauthorized, BadRequest
from lrs.models import Token, Agent
from oauth_provider.utils import send_oauth_error
from oauth_provider.consts import  ACCEPTED

# A decorator, that can be used to authenticate some requests at the site.
def auth(func):
    @wraps(func)
    def inner(request, *args, **kwargs):
        # Note: The cases involving OAUTH_ENABLED are here if OAUTH_ENABLED is switched from true to false
        # after a client has performed the handshake. (Not likely to happen, but could) 
        auth_type = request['auth']['type']
        # There is an http auth_type request and http auth is enabled
        if auth_type == 'http' and settings.HTTP_AUTH_ENABLED:
            http_auth_helper(request)
        # There is an http auth_type request and http auth is not enabled
        elif auth_type == 'http' and not settings.HTTP_AUTH_ENABLED:
            raise BadRequest("HTTP authorization is not enabled. To enable, set the HTTP_AUTH_ENABLED flag to true in settings")
        # There is an oauth auth_type request and oauth is enabled
        elif (auth_type == 'oauth' or auth_type == 'oauth2') and settings.OAUTH_ENABLED: 
            oauth_helper(request)
        # There is an oauth auth_type request and oauth is not enabled
        elif (auth_type == 'oauth' or auth_type == 'oauth2') and not settings.OAUTH_ENABLED: 
            raise BadRequest("OAuth is not enabled. To enable, set the OAUTH_ENABLED flag to true in settings")
        # There is no auth_type request and there is some sort of auth enabled
        elif auth_type == 'none' and (settings.HTTP_AUTH_ENABLED or settings.OAUTH_ENABLED):
            raise Unauthorized("Auth is enabled but no authentication was sent with the request.")
        # There is no auth_type request and no auth is enabled
        elif auth_type == 'none' and not (settings.HTTP_AUTH_ENABLED or settings.OAUTH_ENABLED):
            request['auth'] = None
        return func(request, *args, **kwargs)
    return inner

def http_auth_helper(request):
    if request['headers'].has_key('Authorization'):
        auth = request['headers']['Authorization'].split()
        if len(auth) == 2:
            if auth[0].lower() == 'basic':
                # Currently, only basic http auth is used.
                uname, passwd = base64.b64decode(auth[1]).split(':')
                user = authenticate(username=uname, password=passwd)
                if user:
                    # If the user successfully logged in, then add/overwrite
                    # the user object of this request.
                    request['auth']['id'] = user
                else:
                    raise Unauthorized("Authorization failed, please verify your username and password")
    else:
        # The username/password combo was incorrect, or not provided.
        raise Unauthorized("Authorization header missing")

# TODO - adjust for oauth2
def oauth_helper(request):
    consumer = request['auth']['oauth_consumer']
    token = request['auth']['oauth_token']
    
    # Make sure consumer has been accepted by system
    if consumer.status != ACCEPTED:
        raise OauthUnauthorized(send_oauth_error("%s has not been authorized" % str(consumer.name)))

    # make sure the token is an approved access token
    if token.token_type != Token.ACCESS or not token.is_approved:
        raise OauthUnauthorized(send_oauth_error("The access token is not valid"))
    
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
                                "homePage":"lrs://XAPI/OAuth/token/"
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
    oauth_group, created = Agent.objects.oauth_group(**kwargs)
    request['auth']['id'] = oauth_group
