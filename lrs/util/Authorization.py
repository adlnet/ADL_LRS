import base64
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.sites.models import Site
from django.contrib.auth.models import User

from ..exceptions import Unauthorized, BadRequest, Forbidden
from ..objects.AgentManager import AgentManager
from ..models import Agent

from oauth_provider.models import Consumer
from oauth2_provider.provider.oauth2.models import Client

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
            oauth2_helper(request)
        # There is an oauth auth_type request and oauth is not enabled
        elif (auth_type == 'oauth' or auth_type == 'oauth2') and not settings.OAUTH_ENABLED: 
            raise BadRequest("OAuth is not enabled. To enable, set the OAUTH_ENABLED flag to true in settings")
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
                    request['auth']['authority'] = None
                elif uname or passwd:
                    user = authenticate(username=uname, password=passwd)
                    if user:
                        # If the user successfully logged in, then add/overwrite
                        # the user object of this request.
                        request['auth']['user'] = user
                        request['auth']['authority'] = AgentManager(params={'name':user.username, 'mbox':'mailto:%s' % user.email, 'objectType': 'Agent'},
                            define=True).Agent
                    else:
                        raise Unauthorized("Authorization failed, please verify your username and password")
                request['auth']['define'] = True
    else:
        # The username/password combo was incorrect, or not provided.
        raise Unauthorized("Authorization header missing")

def oauth_helper(request):
    token = request['auth']['oauth_token']
    
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
                                "homePage":"%s://%s/XAPI/OAuth/token/" % (settings.SITE_SCHEME, str(Site.objects.get_current().domain))
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
    request['auth']['authority'] = oauth_group
    request['auth']['user'] = get_user_from_auth(oauth_group)
    validate_oauth_scope(request)

def oauth2_helper(request):
    token = request['auth']['oauth_token']

    user = token.user
    user_name = user.username
    if user.email.startswith('mailto:'):
        user_email = user.email
    else:
        user_email = 'mailto:%s' % user.email
    consumer = token.client
    members = [
                {
                    "account":{
                                "name":consumer.client_id,
                                "homePage":"%s://%s/XAPI/OAuth2/access_token/" % (settings.SITE_SCHEME, str(Site.objects.get_current().domain))
                    },
                    "objectType": "Agent",
                    "oauth_identifier": "anonoauth:%s" % (consumer.client_id)
                },
                {
                    "name":user_name,
                    "mbox":user_email,
                    "objectType": "Agent"
                }
    ]
    kwargs = {"objectType":"Group", "member":members,"oauth_identifier": "anongroup:%s-%s" % (consumer.client_id, user_email)}
    # create/get oauth group and set in dictionary
    oauth_group, created = Agent.objects.oauth_group(**kwargs)
    request['auth']['authority'] = oauth_group
    request['auth']['user'] = get_user_from_auth(oauth_group)
    validate_oauth_scope(request)