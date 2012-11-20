from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth import authenticate
from lrs.exceptions import Unauthorized
import base64
from functools import wraps
import pdb

def http_auth(func):
    """
    A decorator, that can be used to authenticate some requests at the site.
    """
    @wraps(func)
    def inner(request, *args, **kwargs):
        if settings.HTTP_AUTH:
            _http_auth_helper(request)
        return func(request, *args, **kwargs)
    return inner

def _http_auth_helper(request):
    # pdb.set_trace()
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


    