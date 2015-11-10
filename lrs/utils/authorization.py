import base64
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.sites.models import Site
from django.contrib.auth.models import User

from ..exceptions import Unauthorized, BadRequest, Forbidden, OauthUnauthorized, OauthBadRequest
from ..models import Agent

from oauth_provider.models import Consumer
from oauth_provider.utils import get_oauth_request, require_params
from oauth_provider.decorators import CheckOauth
from oauth_provider.store import store
from oauth2_provider.provider.oauth2.models import Client, AccessToken

# A decorator, that can be used to authenticate some requests at the site.
def auth(func):
    @wraps(func)
    def inner(request, *args, **kwargs):
        # Note: The cases involving OAUTH_ENABLED are here if OAUTH_ENABLED is switched from true to false
        # after a client has performed the handshake. (Not likely to happen, but could) 
        auth_type = request['auth']['type']
        # There is an http auth_type request
        if auth_type == 'http':
            http_auth_helper(request)
        elif auth_type == 'oauth' and settings.OAUTH_ENABLED: 
            oauth_helper(request)
        elif auth_type == 'oauth2' and settings.OAUTH_ENABLED:
            oauth_helper(request, 2)
        # There is an oauth auth_type request and oauth is not enabled
        elif (auth_type == 'oauth' or auth_type == 'oauth2') and not settings.OAUTH_ENABLED: 
            raise BadRequest("OAuth is not enabled. To enable, set the OAUTH_ENABLED flag to true in settings")
        return func(request, *args, **kwargs)
    return inner

# Decorater used for non-xapi endpoints
def non_xapi_auth(func):
    @wraps(func)
    def inner(request, *args, **kwargs):
        auth = None
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META.get('HTTP_AUTHORIZATION')
        elif 'Authorization' in request.META:
            auth = request.META.get('Authorization')

        if auth:
            if auth[:6] == 'OAuth ':
                oauth_request = get_oauth_request(request)
                # Returns HttpBadRequest if missing any params
                missing = require_params(oauth_request)            
                if missing:
                    raise missing

                check = CheckOauth()
                e_type, error = check.check_access_token(request)
                if e_type and error:
                    if e_type == 'auth':
                        raise OauthUnauthorized(error)
                    else:
                        raise OauthBadRequest(error)
                # Consumer and token should be clean by now
                consumer = store.get_consumer(request, oauth_request, oauth_request['oauth_consumer_key'])
                token = store.get_access_token(request, oauth_request, consumer, oauth_request.get_parameter('oauth_token'))
                request.META['lrs-user'] = token.user        
            elif auth[:7] == 'Bearer ':
                try:
                    access_token = AccessToken.objects.get(token=auth[7:])
                except AccessToken.DoesNotExist:
                    raise OauthUnauthorized("Access Token does not exist")
                else:
                    if access_token.get_expire_delta() <= 0:
                        raise OauthUnauthorized('Access Token has expired')
                    request.META['lrs-user'] = access_token.user
            else:
                auth = auth.split()
                if len(auth) == 2:
                    if auth[0].lower() == 'basic':
                        uname, passwd = base64.b64decode(auth[1]).split(':')
                        if uname and passwd:
                            user = authenticate(username=uname, password=passwd)
                            if not user:
                                request.META['lrs-user'] = (False, "Unauthorized: Authorization failed, please verify your username and password")
                            request.META['lrs-user'] = (True, user)
                        else:
                            request.META['lrs-user'] = (False, "Unauthorized: The format of the HTTP Basic Authorization Header value is incorrect")
                    else:
                        request.META['lrs-user'] = (False, "Unauthorized: HTTP Basic Authorization Header must start with Basic")
                else:
                    request.META['lrs-user'] = (False, "Unauthorized: The format of the HTTP Basic Authorization Header value is incorrect")
        else:
            request.META['lrs-user'] = (False, "Unauthorized: Authorization must be supplied")                            
        return func(request, *args, **kwargs)
    return inner

def get_user_from_auth(auth):
    if not auth:
        return None
    if type(auth) ==  User:
        return auth #it is a User already
    else:
        oauth = 1
        # it's a group.. gotta find out which of the 2 members is the client
        for member in auth.member.all():
            if member.account_name: 
                key = member.account_name
                if 'oauth2' in member.account_homePage.lower():
                    oauth = 2
                break
        # get consumer/client based on oauth version
        if oauth == 1:
            user = Consumer.objects.get(key__exact=key).user
        else:
            user = Client.objects.get(client_id__exact=key).user
    return user

def validate_oauth_scope(req_dict):
    method = req_dict['method']
    endpoint = req_dict['auth']['endpoint']
    token = req_dict['auth']['oauth_token']
    scopes = token.scope_to_list()

    err_msg = "Incorrect permissions to %s at %s" % (str(method), str(endpoint))

    validator = {'GET':{"/statements": True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                    "/statements/more": True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                    "/activities": True if 'all' in scopes or 'all/read' in scopes else False,
                    "/activities/profile": True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False,
                    "/activities/state": True if 'all' in scopes or 'all/read' in scopes or 'state' in scopes else False,
                    "/agents": True if 'all' in scopes or 'all/read' in scopes else False,
                    "/agents/profile": True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False
                },
             'HEAD':{"/statements": True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                    "/statements/more": True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                    "/activities": True if 'all' in scopes or 'all/read' in scopes else False,
                    "/activities/profile": True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False,
                    "/activities/state": True if 'all' in scopes or 'all/read' in scopes or 'state' in scopes else False,
                    "/agents": True if 'all' in scopes or 'all/read' in scopes else False,
                    "/agents/profile": True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False
                },   
             'PUT':{"/statements": True if 'all' in scopes or 'statements/write' in scopes else False,
                    "/activities": True if 'all' in scopes or 'define' in scopes else False,
                    "/activities/profile": True if 'all' in scopes or 'profile' in scopes else False,
                    "/activities/state": True if 'all' in scopes or 'state' in scopes else False,
                    "/agents": True if 'all' in scopes or 'define' in scopes else False,
                    "/agents/profile": True if 'all' in scopes or 'profile' in scopes else False
                },
             'POST':{"/statements": True if 'all' in scopes or 'statements/write' in scopes else False,
                    "/activities": True if 'all' in scopes or 'define' in scopes else False,
                    "/activities/profile": True if 'all' in scopes or 'profile' in scopes else False,
                    "/activities/state": True if 'all' in scopes or 'state' in scopes else False,
                    "/agents": True if 'all' in scopes or 'define' in scopes else False,
                    "/agents/profile": True if 'all' in scopes or 'profile' in scopes else False
                },
             'DELETE':{"/statements": True if 'all' in scopes or 'statements/write' in scopes else False,
                    "/activities": True if 'all' in scopes or 'define' in scopes else False,
                    "/activities/profile": True if 'all' in scopes or 'profile' in scopes else False,
                    "/activities/state": True if 'all' in scopes or 'state' in scopes else False,
                    "/agents": True if 'all' in scopes or 'define' in scopes else False,
                    "/agents/profile": True if 'all' in scopes or 'profile' in scopes else False
                }
             }

    # Raise forbidden if requesting wrong endpoint or with wrong method than what's in scope
    if not validator[method][endpoint]:
        raise Forbidden(err_msg)

    # Set flag to read only statements owned by user
    if 'statements/read/mine' in scopes:
        req_dict['auth']['statements_mine_only'] = True

    # Set flag for define - allowed to update global representation of activities/agents
    if 'define' in scopes or 'all' in scopes:
        req_dict['auth']['define'] = True
    else:
        req_dict['auth']['define'] = False

def http_auth_helper(request):
    if request['headers'].has_key('Authorization'):
        auth = request['headers']['Authorization'].split()
        if len(auth) == 2:
            if auth[0].lower() == 'basic':
                # Currently, only basic http auth is used.
                uname, passwd = base64.b64decode(auth[1]).split(':')
                # Sent in empty auth - now allowed when not allowing empty auth in settings
                if not uname and not passwd and not settings.ALLOW_EMPTY_HTTP_AUTH:
                    raise BadRequest('Must supply auth credentials')
                elif not uname and not passwd and settings.ALLOW_EMPTY_HTTP_AUTH:
                    request['auth']['user'] = None
                    request['auth']['agent'] = None
                elif uname or passwd:
                    user = authenticate(username=uname, password=passwd)
                    if user:
                        # If the user successfully logged in, then add/overwrite
                        # the user object of this request.
                        request['auth']['user'] = user
                        request['auth']['agent'] = Agent.objects.retrieve_or_create(**{'name':user.username, 'mbox':'mailto:%s' % user.email, 'objectType': 'Agent'})[0]
                    else:
                        raise Unauthorized("Authorization failed, please verify your username and password")
                request['auth']['define'] = True
            else:
                raise Unauthorized("HTTP Basic Authorization Header must start with Basic")
        else:
            raise Unauthorized("The format of the HTTP Basic Authorization Header value is incorrect")
    else:
        # The username/password combo was incorrect, or not provided.
        raise Unauthorized("Authorization header missing")

def oauth_helper(request, version=1):
    token = request['auth']['oauth_token']
    user = token.user
    user_name = user.username
    if user.email.startswith('mailto:'):
        user_email = user.email
    else:
        user_email = 'mailto:%s' % user.email

    if version == 1 :
        consumer = token.consumer                
    else:
        consumer = token.client
    members = [
                {
                    "account":{
                                "name":consumer.key if version == 1 else consumer.client_id,
                                "homePage":"%s://%s/XAPI/OAuth/token/" % (settings.SITE_SCHEME, str(Site.objects.get_current().domain)) if version == 1 else \
                                "%s://%s/XAPI/oauth2/access_token/" % (settings.SITE_SCHEME, str(Site.objects.get_current().domain))
                    },
                    "objectType": "Agent",
                    "oauth_identifier": "anonoauth:%s" % consumer.key if version == 1 else consumer.client_id
                },
                {
                    "name":user_name,
                    "mbox":user_email,
                    "objectType": "Agent"
                }
    ]
    kwargs = {"objectType":"Group", "member":members, "oauth_identifier": "anongroup:%s-%s" % (consumer.key if version == 1 else consumer.client_id, user_email)}
    # create/get oauth group and set in dictionary
    oauth_group, created = Agent.objects.oauth_group(**kwargs)
    request['auth']['agent'] = oauth_group
    request['auth']['user'] = get_user_from_auth(oauth_group)
    validate_oauth_scope(request)