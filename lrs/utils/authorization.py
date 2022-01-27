import base64
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.urls import reverse

from ..exceptions import Unauthorized, BadRequest, Forbidden, OauthUnauthorized, OauthBadRequest
from ..models import Agent

from oauth_provider.models import Consumer
from oauth_provider.utils import get_oauth_request, require_params
from oauth_provider.decorators import CheckOauth
from oauth_provider.store import store

# A decorator, that can be used to authenticate some requests at the site.

def auth(func):
    @wraps(func)
    def inner(request, *args, **kwargs):
        # Note: The cases involving OAUTH_ENABLED are here if OAUTH_ENABLED is switched from true to false
        # after a client has performed the handshake. (Not likely to happen,
        # but could)
        auth_type = request['auth']['type']
        # There is an http auth_type request
        if auth_type == 'http':
            http_auth_helper(request)
        elif auth_type == 'oauth' and settings.OAUTH_ENABLED:
            oauth_helper(request)
        # There is an oauth auth_type request and oauth is not enabled
        elif (auth_type == 'oauth') and not settings.OAUTH_ENABLED:
            raise BadRequest(
                "OAuth is not enabled. To enable, set the OAUTH_ENABLED flag to true in settings")
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
        elif request.user:
            auth = request.user
        if auth:
            if isinstance(auth, str):
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
                    consumer = store.get_consumer(
                        request, oauth_request, oauth_request['oauth_consumer_key'])
                    token = store.get_access_token(
                        request, oauth_request, consumer, oauth_request.get_parameter('oauth_token'))
                    request.META['lrs-user'] = token.user
                else:
                    auth = auth.split()
                    if len(auth) == 2:
                        if auth[0].lower() == 'basic':

                            auth_parsed = decode_base64_string(auth[1])
                            [uname, passwd] = auth_parsed.split(':')
                            
                            if uname and passwd:
                                user = authenticate(
                                    username=uname, password=passwd)
                                if not user:
                                    request.META[
                                        'lrs-user'] = (False, "Unauthorized: Authorization failed, please verify your username and password")
                                request.META['lrs-user'] = (True, user)
                            else:
                                request.META[
                                    'lrs-user'] = (False, "Unauthorized: The format of the HTTP Basic Authorization Header value is incorrect")
                        else:
                            request.META[
                                'lrs-user'] = (False, "Unauthorized: HTTP Basic Authorization Header must start with Basic")
                    else:
                        request.META[
                            'lrs-user'] = (False, "Unauthorized: The format of the HTTP Basic Authorization Header value is incorrect")
            else:
                request.META['lrs-user'] = (True, '')
        else:
            request.META[
                'lrs-user'] = (False, "Unauthorized: Authorization must be supplied")
        return func(request, *args, **kwargs)
    return inner

def decode_base64_string(base64_message):
    base64_bytes = base64_message.encode("ascii")
    message_bytes = base64.b64decode(base64_bytes)
    message = message_bytes.decode("ascii")

    return message

def get_user_from_auth(auth):
    if not auth:
        return None
    if type(auth) == User:
        return auth  # it is a User already
    else:
        # it's a group.. gotta find out which of the 2 members is the client
        for member in auth.member.all():
            if member.account_name:
                key = member.account_name
                break
        user = Consumer.objects.get(key__exact=key).user
    return user


def validate_oauth_scope(req_dict):
    method = req_dict['method']
    endpoint = req_dict['auth']['endpoint']
    if '/statements/more' in endpoint:
        endpoint = "%s/%s" % (reverse('lrs:statements').lower(), "more")
    
    token = req_dict['auth']['oauth_token']
    scopes = token.scope_to_list()

    err_msg = "Incorrect permissions to %s at %s" % (
        str(method), str(endpoint))

    validator = {'GET': {reverse('lrs:statements').lower(): True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                         reverse('lrs:statements_more_placeholder').lower(): True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                         reverse('lrs:activities').lower(): True if 'all' in scopes or 'all/read' in scopes else False,
                         reverse('lrs:activity_profile').lower(): True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False,
                         reverse('lrs:activity_state').lower(): True if 'all' in scopes or 'all/read' in scopes or 'state' in scopes else False,
                         reverse('lrs:agents').lower(): True if 'all' in scopes or 'all/read' in scopes else False,
                         reverse('lrs:agent_profile').lower(): True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False
                         },
                 'HEAD': {reverse('lrs:statements').lower(): True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                          reverse('lrs:statements_more_placeholder').lower(): True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                          reverse('lrs:activities').lower(): True if 'all' in scopes or 'all/read' in scopes else False,
                          reverse('lrs:activity_profile').lower(): True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False,
                          reverse('lrs:activity_state').lower(): True if 'all' in scopes or 'all/read' in scopes or 'state' in scopes else False,
                          reverse('lrs:agents').lower(): True if 'all' in scopes or 'all/read' in scopes else False,
                          reverse('lrs:agent_profile').lower(): True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False
                          },
                 'PUT': {reverse('lrs:statements').lower(): True if 'all' in scopes or 'statements/write' in scopes else False,
                         reverse('lrs:activity_profile').lower(): True if 'all' in scopes or 'profile' in scopes else False,
                         reverse('lrs:activity_state').lower(): True if 'all' in scopes or 'state' in scopes else False,
                         reverse('lrs:agent_profile').lower(): True if 'all' in scopes or 'profile' in scopes else False
                         },
                 'POST': {reverse('lrs:statements').lower(): True if 'all' in scopes or 'statements/write' in scopes else False,
                          reverse('lrs:activity_profile').lower(): True if 'all' in scopes or 'profile' in scopes else False,
                          reverse('lrs:activity_state').lower(): True if 'all' in scopes or 'state' in scopes else False,
                          reverse('lrs:agent_profile').lower(): True if 'all' in scopes or 'profile' in scopes else False
                          },
                 'DELETE': {reverse('lrs:activity_profile').lower(): True if 'all' in scopes or 'profile' in scopes else False,
                            reverse('lrs:activity_state').lower(): True if 'all' in scopes or 'state' in scopes else False,
                            reverse('lrs:agent_profile').lower(): True if 'all' in scopes or 'profile' in scopes else False
                            }
                 }

    # Raise forbidden if requesting wrong endpoint or with wrong method than
    # what's in scope
    if not validator[method][endpoint]:
        raise Forbidden(err_msg)

    # Set flag to read only statements owned by user
    if 'statements/read/mine' in scopes:
        req_dict['auth']['statements_mine_only'] = True

    # Set flag for define - allowed to update global representation of
    # activities/agents
    if 'define' in scopes or 'all' in scopes:
        req_dict['auth']['define'] = True
    else:
        req_dict['auth']['define'] = False


def http_auth_helper(request):
    if 'Authorization' in request['headers']:
        auth = request['headers']['Authorization'].split()
        if len(auth) == 2:
            if auth[0].lower() == 'basic':
                # Currently, only basic http auth is used.
                auth_parsed = decode_base64_string(auth[1])
                try:
                    auth_parsed = decode_base64_string(auth[1])
                    [uname, passwd] = auth_parsed.split(':')
                except Exception as e:
                    raise BadRequest(f"Authorization failure: {e}, {auth[1]} was type {type(auth[1])} -> {auth_parsed}")
                # Sent in empty auth - now allowed when not allowing empty auth
                # in settings
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
                        try:
                            request['auth']['agent'] = user.agent    
                        except Exception:
                            # Gets here if for some reason the agent is deleted
                            agent = Agent.objects.retrieve_or_create(
                                **{'name': user.username, 'mbox': 'mailto:%s' % user.email, \
                                'objectType': 'Agent'})[0]
                            agent.user = user
                            agent.save()
                            request['auth']['agent'] = user.agent
                    else:
                        raise Unauthorized(
                            "Authorization failed, please verify your username and password")
                request['auth']['define'] = True
            else:
                raise Unauthorized(
                    "HTTP Basic Authorization Header must start with Basic")
        else:
            raise Unauthorized(
                "The format of the HTTP Basic Authorization Header value is incorrect")
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
            "account": {
                "name": consumer.key,
                "homePage": "%s://%s/XAPI/OAuth/token/" % (request['scheme'],
                    request['domain'])
            },
            "objectType": "Agent",
            "oauth_identifier": "anonoauth:%s" % consumer.key
        },
        {
            "name": user_name,
            "mbox": user_email,
            "objectType": "Agent"
        }
    ]
    kwargs = {"objectType": "Group", "member": members,
              "oauth_identifier": "anongroup:%s-%s" % (consumer.key, user_email)}
    # create/get oauth group and set in dictionary
    oauth_group, created = Agent.objects.oauth_group(**kwargs)
    request['auth']['agent'] = oauth_group
    request['auth']['user'] = get_user_from_auth(oauth_group)
    validate_oauth_scope(request)
