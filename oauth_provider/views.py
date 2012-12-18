from oauth.oauth import OAuthError

from django.conf import settings
from django.http import (
    HttpResponse, HttpResponseBadRequest, HttpResponseRedirect)
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import get_callable

from django.template import RequestContext
from utils import initialize_server_request, send_oauth_error
from decorators import oauth_required
from stores import check_valid_callback
from consts import OUT_OF_BAND
from django.utils.decorators import decorator_from_middleware
from lrs.util import TCAPIversionHeaderMiddleware
import uuid
import pdb
from django.shortcuts import render_to_response

OAUTH_AUTHORIZE_VIEW = 'OAUTH_AUTHORIZE_VIEW'
OAUTH_CALLBACK_VIEW = 'OAUTH_CALLBACK_VIEW'
INVALID_PARAMS_RESPONSE = send_oauth_error(OAuthError(
                                            _('Invalid request parameters.')))

def oauth_home(request):
    rsp = """
    <html><head></head><body><h1>Oauth Authorize</h1></body></html>"""
    return HttpResponse(rsp)

@decorator_from_middleware(TCAPIversionHeaderMiddleware.TCAPIversionHeaderMiddleware)
def request_token(request):
    """
    The Consumer obtains an unauthorized Request Token by asking the Service 
    Provider to issue a Token. The Request Token's sole purpose is to receive 
    User approval and can only be used to obtain an Access Token.
    """
    # If oauth is not enabled, don't initiate the handshake
    if settings.OAUTH_ENABLED:
        oauth_server, oauth_request = initialize_server_request(request)
        if oauth_server is None:
            return INVALID_PARAMS_RESPONSE
        try:
            # create a request token
            token = oauth_server.fetch_request_token(oauth_request)
            # return the token
            response = HttpResponse(token.to_string(), mimetype="text/plain")
        except OAuthError, err:
            response = send_oauth_error(err)
        return response
    else:
        return HttpResponseBadRequest("OAuth is not enabled. To enable, set the OAUTH_ENABLED flag to true in settings")

@decorator_from_middleware(TCAPIversionHeaderMiddleware.TCAPIversionHeaderMiddleware)    
def user_authorization(request):
    """
    The Consumer cannot use the Request Token until it has been authorized by 
    the User.
    """
    # pdb.set_trace()
    oauth_server, oauth_request = initialize_server_request(request)
    if oauth_request is None:
        return INVALID_PARAMS_RESPONSE
    try:
        # get the request token
        token = oauth_server.fetch_request_token(oauth_request)
    except OAuthError, err:
        return send_oauth_error(err)

    try:
        # get the request callback, though there might not be one
        callback = oauth_server.get_callback(oauth_request)
        
        # OAuth 1.0a: this parameter should not be present on this version
        if token.callback_confirmed:
            return HttpResponseBadRequest("Cannot specify oauth_callback at authorization step for 1.0a protocol")
        if not check_valid_callback(callback):
            return HttpResponseBadRequest("Invalid callback URL")
    except OAuthError:
        callback = None

    # OAuth 1.0a: use the token's callback if confirmed
    if token.callback_confirmed:
        callback = token.callback
        if callback == OUT_OF_BAND:
            callback = None

    # entry point for the user
    if request.method == 'GET':
        # try to get custom authorize view
        authorize_view_str = getattr(settings, OAUTH_AUTHORIZE_VIEW, 
                                    'oauth_provider.views.authorize_client')
        try:
            authorize_view = get_callable(authorize_view_str)
        except AttributeError:
            raise Exception, "%s view doesn't exist." % authorize_view_str
        params = oauth_request.get_normalized_parameters()
        # set the oauth flag
        request.session['oauth'] = token.key
        return authorize_view(request, token, callback, params)
    
    # user grant access to the service
    elif request.method == 'POST':
        # verify the oauth flag set in previous GET
        if request.session.get('oauth', '') == token.key:
            request.session['oauth'] = ''
            try:
                if int(request.POST.get('authorize_access', 0)):
                    # authorize the token
                    token = oauth_server.authorize_token(token, request.user)
                    # return the token key
                    args = { 'token': token }
                else:
                    args = { 'error': _('Access not granted by user.') }
            except OAuthError, err:
                response = send_oauth_error(err)
            if callback:
                if "?" in callback:
                    url_delimiter = "&"
                else:
                    url_delimiter = "?"
                if 'token' in args:
                    query_args = args['token'].to_string(only_key=True)
                else: # access is not authorized i.e. error
                    query_args = 'error=%s' % args['error']
                response = HttpResponseRedirect('%s%s%s' % (callback, url_delimiter, query_args))
            else:
                # try to get custom callback view
                callback_view_str = getattr(settings, OAUTH_CALLBACK_VIEW,
                                    'oauth_provider.views.callback_view')
                try:
                    callback_view = get_callable(callback_view_str)
                except AttributeError:
                    raise Exception, "%s view doesn't exist." % callback_view_str
                response = callback_view(request, **args)
        else:
            response = send_oauth_error(OAuthError(_('Action not allowed.')))
        return response

@decorator_from_middleware(TCAPIversionHeaderMiddleware.TCAPIversionHeaderMiddleware)    
def access_token(request):    
    """
    The Consumer exchanges the Request Token for an Access Token capable of 
    accessing the Protected Resources.
    """
    oauth_server, oauth_request = initialize_server_request(request)
    if oauth_request is None:
        return INVALID_PARAMS_RESPONSE
    try:
        # get the request token
        token = oauth_server.fetch_access_token(oauth_request)
        # return the token
        response = HttpResponse(token.to_string(), mimetype="text/plain")
    except OAuthError, err:
        response = send_oauth_error(err)
    return response

# @login_required
# def fake_authorize_view(request, token, callback, params):
#     """
#     Fake view for tests. It must return an ``HttpResponse``.
    
#     You need to define your own in ``settings.OAUTH_AUTHORIZE_VIEW``.
#     """
#     return HttpResponse('Fake authorize view for %s.' % token.consumer.name)

def authorize_client(request, token, callback, params):
        existing_lrs_auth_id = token.lrs_auth_id
        if not existing_lrs_auth_id:
            lrs_auth_id = str(uuid.uuid4())
            token.lrs_auth_id = lrs_auth_id
            token.save()
        else:
            lrs_auth_id = existing_lrs_auth_id
        return render_to_response('oauth_allow_client.html', {"lrs_auth_id": lrs_auth_id},
            context_instance=RequestContext(request))

def callback_view(request, **args):
    if 'error' in args:
        return HttpResponse("Error - %s" % args['error'])

    return HttpResponse("Callback view. - You've been authenticated!")