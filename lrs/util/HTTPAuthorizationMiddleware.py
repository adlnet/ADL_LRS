"""
Use HTTP Authorization to log in to django site.

If you use the FORCE_HTTP_AUTH=True in your settings.py, then ONLY
Http Auth will be used, if you don't then either http auth or 
django's session-based auth will be used.

If you provide a HTTP_AUTH_REALM in your settings, that will be used as
the realm for the challenge.

"""
        
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth import authenticate
from lrs.exceptions import Unauthorized
import base64
from functools import wraps
import pdb

class HTTPAuthorizationMiddleware(object):
    """
    Some middleware to authenticate all requests at this site.
    """
    def process_request(self, request):
        return _http_auth_helper(request)

def http_auth(func):
    """
    A decorator, that can be used to authenticate some requests at the site.
    """
    @wraps(func)
    def inner(request, *args, **kwargs):
        _http_auth_helper(request)
        return func(request, *args, **kwargs)
    return inner

def _http_auth_helper(request):
    "This is the part that does all of the work"
    try:
        if not settings.FORCE_HTTP_AUTH:
            # If we don't mind if django's session auth is used, see if the
            # user is already logged in, and use that user.
            if request.user:
                return None
    except AttributeError:
        pass
        
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
        raise Unauthorized("Auth Required")


    