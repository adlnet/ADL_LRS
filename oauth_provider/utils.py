from oauth.oauth import OAuthRequest, OAuthServer, build_authenticate_header,\
    OAuthSignatureMethod_PLAINTEXT, OAuthSignatureMethod_HMAC_SHA1

from django.conf import settings
from django.http import HttpResponse

from stores import DataStore
import pdb
import ast

OAUTH_REALM_KEY_NAME = getattr(settings, 'OAUTH_REALM_KEY_NAME', '')
OAUTH_SIGNATURE_METHODS = getattr(settings, 'OAUTH_SIGNATURE_METHODS', ['plaintext', 'hmac-sha1'])

def initialize_server_request(request):
    """Shortcut for initialization."""
    # OAuth change
    # Django converts Authorization header in HTTP_AUTHORIZATION
    # Warning: it doesn't happen in tests but it's useful, do not remove!

    auth_header = {}
    if 'Authorization' in request.META:
        auth_header = {'Authorization': request.META['Authorization']}
    elif 'HTTP_AUTHORIZATION' in request.META:
        auth_header =  {'Authorization': request.META['HTTP_AUTHORIZATION']}
   
    # Don't include extra parameters when request.method is POST and 
    # request.MIME['CONTENT_TYPE'] is "application/x-www-form-urlencoded" 
    # (See http://oauth.net/core/1.0a/#consumer_req_param).
    # But there is an issue with Django's test Client and custom content types
    # so an ugly test is made here, if you find a better solution...
    parameters = {}        
    if request.method == "POST" and \
        (request.META.get('CONTENT_TYPE') == "application/x-www-form-urlencoded" \
            or request.META.get('SERVER_NAME') == 'testserver'):
        # lou -w -When POST statement data, the actual data is a dict key and has a value of ''
        # have to parse it out correctly...
        p = dict(request.POST.items()) 
        if p.values()[0] == '':
            parameters = ast.literal_eval(p.keys()[0])
        else:
            parameters = p
    
    oauth_request = OAuthRequest.from_request(request.method, 
                                              request.build_absolute_uri(), 
                                              headers=auth_header,
                                              parameters=parameters,
                                              query_string=request.META.get('QUERY_STRING', ''))
    if oauth_request:
        oauth_server = OAuthServer(DataStore(oauth_request))
        if 'plaintext' in OAUTH_SIGNATURE_METHODS:
            oauth_server.add_signature_method(OAuthSignatureMethod_PLAINTEXT())
        if 'hmac-sha1' in OAUTH_SIGNATURE_METHODS:
            oauth_server.add_signature_method(OAuthSignatureMethod_HMAC_SHA1())
    else:
        oauth_server = None
    return oauth_server, oauth_request

def send_oauth_error(err=None):
    """Shortcut for sending an error."""
    # send a 401 error
    # lou w - be able to send plain error messages
    if isinstance(err, str):
        response = HttpResponse(err, mimetype="text/plain")
    else:
        response = HttpResponse(err.message.encode('utf-8'), mimetype="text/plain")
    response.status_code = 401
    # return the authenticate header
    header = build_authenticate_header(realm=OAUTH_REALM_KEY_NAME)
    for k, v in header.iteritems():
        response[k] = v
    return response
