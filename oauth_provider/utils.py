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
    # Django converts Authorization header in HTTP_AUTHORIZATION
    # Warning: it doesn't happen in tests but it's useful, do not remove!
    
    # Check to see if it's a dict if it's being called from the LRS app. The LRS app parses everything in a dict first
    # then will call this in Authorization with the request dict.
    if type(request) == dict:
        auth_header = {}
        if 'Authorization' in request:
            auth_header = {'Authorization': request['Authorization']}
        elif 'HTTP_AUTHORIZATION' in request:
            auth_header =  {'Authorization': request['HTTP_AUTHORIZATION']}

        parameters = {}
        # TODO-WHAT TO DO WITH THIS?
        # if request['method'] == "POST":
        #     parameters = ast.literal_eval(request['body'])       

        oauth_request = OAuthRequest.from_request(request['method'], 
                                                  request['absolute_uri'], 
                                                  headers=auth_header,
                                                  parameters=parameters,
                                                  query_string=request['query_string'])
    else:
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
            parameters = dict(request.REQUEST.items())
        # pdb.set_trace() 
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
    # pdb.set_trace()
    response = HttpResponse(err.message.encode('utf-8'), mimetype="text/plain")
    response.status_code = 401
    # return the authenticate header
    header = build_authenticate_header(realm=OAUTH_REALM_KEY_NAME)
    for k, v in header.iteritems():
        response[k] = v
    return response
