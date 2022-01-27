import ast
import binascii
import urllib.request, urllib.parse, urllib.error
import oauth2 as oauth
from urllib.parse import urlparse, urlunparse

from Crypto.PublicKey import RSA
from Crypto.Util.number import long_to_bytes, bytes_to_long
from hashlib import sha1 as sha

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth import authenticate

from .consts import MAX_URL_LENGTH

OAUTH_REALM_KEY_NAME = getattr(settings, 'OAUTH_REALM_KEY_NAME', '')
OAUTH_SIGNATURE_METHODS = getattr(settings, 'OAUTH_SIGNATURE_METHODS', [
                                  'plaintext', 'hmac-sha1', 'rsa-sha1'])
OAUTH_BLACKLISTED_HOSTNAMES = getattr(
    settings, 'OAUTH_BLACKLISTED_HOSTNAMES', [])


def initialize_server_request(request):
    """Shortcut for initialization."""
    oauth_request = get_oauth_request(request)

    if oauth_request:
        oauth_server = oauth.Server()
        if 'plaintext' in OAUTH_SIGNATURE_METHODS:
            oauth_server.add_signature_method(
                oauth.SignatureMethod_PLAINTEXT())
        if 'hmac-sha1' in OAUTH_SIGNATURE_METHODS:
            oauth_server.add_signature_method(
                oauth.SignatureMethod_HMAC_SHA1())
        if 'rsa-sha1' in OAUTH_SIGNATURE_METHODS:
            oauth_server.add_signature_method(SignatureMethod_RSA_SHA1())
    else:
        oauth_server = None
    return oauth_server, oauth_request


def send_oauth_error(scheme, domain, err=None):
    """Shortcut for sending an error."""
    # send a 401 error
    # LRS CHANGE - BE ABLE TO SEND PLAIN TEXT ERROR MESSAGES
    # LRS CHANGE - DECIDE IF 400 OR 401 ERROR
    if isinstance(err, str):
        response = HttpResponse(err, content_type="text/plain")
    else:
        response = HttpResponse(str(err).encode(
            'utf-8'), content_type="text/plain")

    response.status_code = 401
    # return the authenticate header
    header = oauth.build_authenticate_header(realm='%s://%s/xAPI' % (scheme, domain))
    for k, v in header.items():
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
        auth_header = {'Authorization': request.META['HTTP_AUTHORIZATION']}

    # include POST parameters if content type is
    # 'application/x-www-form-urlencoded' and request
    # see: http://tools.ietf.org/html/rfc5849#section-3.4.1.3.1
    parameters = {}
    # if request.method == "POST" and request.META.get('CONTENT_TYPE') == "application/x-www-form-urlencoded":
    #     parameters = dict((k, v.encode('utf-8')) for (k, v) in request.POST.iteritems())

    if request.method == "POST" and request.META.get('CONTENT_TYPE') == "application/x-www-form-urlencoded":
        # LRS CHANGE - DJANGO TEST CLIENT SENDS PARAMS FUNKY-NEED SPECIAL CASE
        if request.META.get('SERVER_NAME') == 'testserver':
            parameters = ast.literal_eval(list(request.POST.items())[0][0])
        else:
            parameters = dict((k, v.encode('utf-8'))
                              for (k, v) in request.POST.items())

    absolute_uri = request.build_absolute_uri(request.path)

    if "HTTP_X_FORWARDED_PROTO" in request.META:
        scheme = request.META["HTTP_X_FORWARDED_PROTO"]
        absolute_uri = urlunparse((scheme, ) + urlparse(absolute_uri)[1:])

    return oauth.Request.from_request(request.method,
                                      absolute_uri,
                                      headers=auth_header,
                                      parameters=parameters,
                                      query_string=request.META.get(
                                          'QUERY_STRING', '')
                                      )


def verify_oauth_request(request, oauth_request, consumer, token=None):
    """ Helper function to verify requests. """
    from .store import store

    # Check nonce
    if not store.check_nonce(request, oauth_request, oauth_request['oauth_nonce'], oauth_request['oauth_timestamp']):
        return False

    # Verify request
    try:
        oauth_server = oauth.Server()
        oauth_server.add_signature_method(oauth.SignatureMethod_HMAC_SHA1())
        oauth_server.add_signature_method(oauth.SignatureMethod_PLAINTEXT())
        oauth_server.add_signature_method(SignatureMethod_RSA_SHA1())

        # Ensure the passed keys and secrets are ascii, or HMAC will complain.
        consumer = oauth.Consumer(consumer.key.encode(
            'ascii', 'ignore'), consumer.secret.encode('ascii', 'ignore'))
        if token is not None:
            token = oauth.Token(token.key.encode(
                'ascii', 'ignore'), token.secret.encode('ascii', 'ignore'))

        oauth_server.verify_request(oauth_request, consumer, token)
    except oauth.Error:
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
    return (callback_url.scheme and
            callback_url.hostname not in OAUTH_BLACKLISTED_HOSTNAMES and
            len(callback) < MAX_URL_LENGTH)

# LRS CHANGE - ADDED ESCAPE FUNCTION AND RSA_SHA1 CLASS (MISSING BEFORE)


def escape(s):
    """Escape a URL including any /."""
    return urllib.parse.quote(s, safe='~')


class SignatureMethod_RSA_SHA1(oauth.SignatureMethod):
    name = 'RSA-SHA1'

    def signing_base(self, request, consumer, token):
        if request.normalized_url is None:
            raise ValueError("Base URL for request is not set.")

        sig = (
            escape(request.method),
            escape(request.normalized_url),
            escape(request.get_normalized_parameters()),
        )

        # If incoming consumer is Consumer model
        if hasattr(consumer, 'id'):
            key = consumer.generate_rsa_key()
        # If incoming consumer is consumer object from verify
        else:
            key = RSA.importKey(consumer.secret)

        raw = '&'.join(sig)
        return key, raw

    def sign(self, request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.signing_base(request, consumer, token)

        digest = sha(raw).digest()
        sig = key.sign(self._pkcs1imify(key, digest), '')[0]
        sig_bytes = long_to_bytes(sig)
        # Calculate the digest base 64.
        return binascii.b2a_base64(sig_bytes)[:-1]

    def check(self, request, consumer, token, signature):
        """Return whether the given signature is the correct signature for
        the given consumer and token signing the given request."""
        key, raw = self.signing_base(request, consumer, token)

        digest = sha(raw).digest()
        sig = bytes_to_long(binascii.a2b_base64(signature))
        data = self._pkcs1imify(key, digest)

        pubkey = key.publickey()
        return pubkey.verify(data, (sig,))

    @staticmethod
    def _pkcs1imify(key, data):
        """Adapted from paramiko

        turn a 20-bte SHA1 hash into a blob of data as large as the key's N,
        using PKCS1's \"emsa-pkcs-v1_5\" encoding.
        """
        SHA1_DIGESTINFO = '\x30\x21\x30\x09\x06\x05\x2b\x0e\x03\x02\x1a\x05\x00\x04\x14'
        size = len(long_to_bytes(key.n))
        filler = '\xff' * (size - len(SHA1_DIGESTINFO) - len(data) - 3)
        return '\x00\x01' + filler + '\x00' + SHA1_DIGESTINFO + data
