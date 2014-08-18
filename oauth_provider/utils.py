import ast
import oauth2 as oauth
from urlparse import urlparse, urlunparse

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth import authenticate

from consts import MAX_URL_LENGTH

OAUTH_REALM_KEY_NAME = getattr(settings, 'OAUTH_REALM_KEY_NAME', '')
OAUTH_SIGNATURE_METHODS = getattr(settings, 'OAUTH_SIGNATURE_METHODS', ['plaintext', 'hmac-sha1'])
OAUTH_BLACKLISTED_HOSTNAMES = getattr(settings, 'OAUTH_BLACKLISTED_HOSTNAMES', [])

def initialize_server_request(request):
    """Shortcut for initialization."""
    oauth_request = get_oauth_request(request)

    if oauth_request:
        oauth_server = oauth.Server()
        if 'plaintext' in OAUTH_SIGNATURE_METHODS:
            oauth_server.add_signature_method(oauth.SignatureMethod_PLAINTEXT())
        if 'hmac-sha1' in OAUTH_SIGNATURE_METHODS:
            oauth_server.add_signature_method(oauth.SignatureMethod_HMAC_SHA1())
    else:
        oauth_server = None
    return oauth_server, oauth_request

def send_oauth_error(err=None):
    """Shortcut for sending an error."""
    # send a 401 error
    # LRS CHANGE - BE ABLE TO SEND PLAIN TEXT ERROR MESSAGES
    # LRS CHANGE - DECIDE IF 400 OR 401 ERROR
    if isinstance(err, basestring):
        response = HttpResponse(err, mimetype="text/plain")
    else:
        response = HttpResponse(err.message.encode('utf-8'), mimetype="text/plain")
    
    response.status_code = 401
    # return the authenticate header
    header = oauth.build_authenticate_header(realm=OAUTH_REALM_KEY_NAME)
    for k, v in header.iteritems():
        response[k] = v
    return response

def get_oauth_request(request):
    """ Converts a Django request object into an `oauth2.Request` object. """
    # Django converts Authorization header in HTTP_AUTHORIZATION
    # Warning: it doesn't happen in tests but it's useful, do not remove!
    auth_header = {}
    if 'Authorization' in request.META:
        auth_header = {'Authorization': request.META['Authorization']}
    elif 'HTTP_AUTHORIZATION' in request.META:
        auth_header =  {'Authorization': request.META['HTTP_AUTHORIZATION']}


    # include POST parameters if content type is
    # 'application/x-www-form-urlencoded' and request
    # see: http://tools.ietf.org/html/rfc5849#section-3.4.1.3.1
    parameters = {}
    # if request.method == "POST" and request.META.get('CONTENT_TYPE') == "application/x-www-form-urlencoded":
    #     parameters = dict((k, v.encode('utf-8')) for (k, v) in request.POST.iteritems())

    if request.method == "POST" and request.META.get('CONTENT_TYPE') == "application/x-www-form-urlencoded":
        # LRS CHANGE - DJANGO TEST CLIENT SENDS PARAMS FUNKY-NEED SPECIAL CASE
        if request.META.get('SERVER_NAME') == 'testserver':
            parameters = ast.literal_eval(request.POST.items()[0][0])
        else:
            parameters = dict((k, v.encode('utf-8')) for (k, v) in request.POST.iteritems())

    absolute_uri = request.build_absolute_uri(request.path)

    if "HTTP_X_FORWARDED_PROTO" in request.META:
        scheme = request.META["HTTP_X_FORWARDED_PROTO"]
        absolute_uri = urlunparse((scheme, ) + urlparse(absolute_uri)[1:])

    return oauth.Request.from_request(request.method,
        absolute_uri,
        headers=auth_header,
        parameters=parameters,
        query_string=request.META.get('QUERY_STRING', '')
    )

def verify_oauth_request(request, oauth_request, consumer, token=None):
    """ Helper function to verify requests. """
    from store import store

    # Check nonce
    if not store.check_nonce(request, oauth_request, oauth_request['oauth_nonce'], oauth_request['oauth_timestamp']):
        return False

    # Verify request
    try:
        oauth_server = oauth.Server()
        oauth_server.add_signature_method(oauth.SignatureMethod_HMAC_SHA1())
        oauth_server.add_signature_method(oauth.SignatureMethod_PLAINTEXT())

        # Ensure the passed keys and secrets are ascii, or HMAC will complain.
        consumer = oauth.Consumer(consumer.key.encode('ascii', 'ignore'), consumer.secret.encode('ascii', 'ignore'))
        if token is not None:
            token = oauth.Token(token.key.encode('ascii', 'ignore'), token.secret.encode('ascii', 'ignore'))

        oauth_server.verify_request(oauth_request, consumer, token)
    except oauth.Error, err:
        return False

    return True

def is_xauth_request(request):
    return request.get('x_auth_password') and request.get('x_auth_username') 

def verify_xauth_request(request, oauth_request):
    """
    Helper function to verify xAuth requests.

    Returns a user if valid or None otherwise
    """
    user = authenticate(
        x_auth_username=oauth_request.get_parameter('x_auth_username'),
        x_auth_password=oauth_request.get_parameter('x_auth_password'),
        x_auth_mode=oauth_request.get_parameter('x_auth_mode')
    )

    if user:
        request.user = user
    return user

def require_params(oauth_request, parameters=None):
    """ Ensures that the request contains all required parameters. """
    params = [
        'oauth_consumer_key',
        'oauth_nonce',
        'oauth_signature',
        'oauth_signature_method',
        'oauth_timestamp'
    ]
    if parameters:
        params.extend(parameters)

    missing = list(param for param in params if param not in oauth_request)
    if missing:
        return HttpResponseBadRequest('Missing OAuth parameters: %s' % (', '.join(missing)))

    return None


def check_valid_callback(callback):
    """
    Checks the size and nature of the callback.
    """
    callback_url = urlparse(callback)
    return (callback_url.scheme
            and callback_url.hostname not in OAUTH_BLACKLISTED_HOSTNAMES
            and len(callback) < MAX_URL_LENGTH)