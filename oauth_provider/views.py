import oauth2 as oauth
import json
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext as _
from django.urls import get_callable
from django.shortcuts import render
from django.template import RequestContext

from oauth_provider.forms import AuthorizeRequestTokenForm
from oauth_provider.compat import UnsafeRedirect

from .store import store, InvalidConsumerError, InvalidTokenError
from .utils import verify_oauth_request, get_oauth_request, require_params, send_oauth_error
from .utils import is_xauth_request
from .consts import OUT_OF_BAND
from .models import Token

OAUTH_AUTHORIZE_VIEW = 'OAUTH_AUTHORIZE_VIEW'
OAUTH_CALLBACK_VIEW = 'OAUTH_CALLBACK_VIEW'

UNSAFE_REDIRECTS = getattr(settings, "OAUTH_UNSAFE_REDIRECTS", False)


@csrf_exempt
def request_token(request):
    oauth_request = get_oauth_request(request)
    if oauth_request is None:
        return HttpResponseBadRequest('Invalid request parameters.')

    missing_params = require_params(oauth_request, ('oauth_callback',))
    if missing_params is not None:
        return missing_params

    if is_xauth_request(oauth_request):
        return HttpResponseBadRequest('xAuth not allowed for this method.')

    try:
        consumer = store.get_consumer(
            request, oauth_request, oauth_request['oauth_consumer_key'])
    except InvalidConsumerError:
        return HttpResponse('Invalid consumer.', status=401)

    if not verify_oauth_request(request, oauth_request, consumer):
        return HttpResponseBadRequest('Could not verify OAuth request.')

    try:
        request_token = store.create_request_token(
            request, oauth_request, consumer, oauth_request['oauth_callback'])
    except oauth.Error:
        return HttpResponse('Invalid request token: %s' % oauth_request.get_parameter('oauth_token'), status=401)

    ret = urlencode({
        'oauth_token': request_token.key,
        'oauth_token_secret': request_token.secret,
        'oauth_callback_confirmed': 'true'
    })
    return HttpResponse(ret, content_type='application/x-www-form-urlencoded')

# LRS CHANGE - CHANGED FORM_CLASS TO OUR CUSTOM FORM


@login_required(login_url="/accounts/login")
def user_authorization(request, form_class=AuthorizeRequestTokenForm):
    if request.method.lower() == 'get':
        if 'oauth_token' not in request.GET:
            return HttpResponseBadRequest('No request token specified.')
        incoming_token = request.GET['oauth_token']
    elif request.method.lower() == 'post':
        if 'oauth_token' not in request.POST:
            return HttpResponseBadRequest('No request token specified.')
        incoming_token = request.POST['oauth_token']

    oauth_request = get_oauth_request(request)

    try:
        request_token = store.get_request_token(
            request, oauth_request, incoming_token)
    except InvalidTokenError:
        return HttpResponse('Invalid request token: %s' % incoming_token, status=401)

    consumer = store.get_consumer_for_request_token(
        request, oauth_request, request_token)

    # LRS CHANGE - MAKE SURE LOGGED IN USER OWNS THIS CONSUMER
    if request.user != consumer.user:
        return HttpResponseForbidden('Invalid user for this client.')

    if request.method == 'POST':
        form = form_class(request.POST)
        if request.session.get('oauth', '') == request_token.key and form.is_valid():
            request.session['oauth'] = ''
            if form.cleaned_data['authorize_access']:
                request_token = store.authorize_request_token(
                    request, oauth_request, request_token)
                args = {'oauth_token': request_token.key}
            else:
                args = {'error': _('Access not granted by user.')}
            if request_token.callback is not None and request_token.callback != OUT_OF_BAND:
                callback_url = request_token.get_callback_url(args)
                if UNSAFE_REDIRECTS:
                    response = UnsafeRedirect(callback_url)
                else:
                    response = HttpResponseRedirect(callback_url)
            else:
                # try to get custom callback view
                callback_view_str = getattr(settings, OAUTH_CALLBACK_VIEW,
                                            'oauth_provider.views.fake_callback_view')
                try:
                    view_callable = get_callable(callback_view_str)
                except AttributeError:
                    raise Exception("%s view doesn't exist." % callback_view_str)

                # try to treat it as Class Based View (CBV)
                try:
                    callback_view = view_callable.as_view()
                except AttributeError:
                    # if it appears not to be CBV treat it like FBV
                    callback_view = view_callable

                response = callback_view(request, **args)
        else:
            response = send_oauth_error('https' if request.is_secure() else 'http',
                get_current_site(request).domain,
                oauth.Error(_('Action not allowed.')))
    else:
        # try to get custom authorize view
        authorize_view_str = getattr(settings, OAUTH_AUTHORIZE_VIEW,
                                     'oauth_provider.views.fake_authorize_view')
        try:
            view_callable = get_callable(authorize_view_str)
        except AttributeError:
            raise Exception("%s view doesn't exist." % authorize_view_str)

        # try to treat it as Class Based View (CBV)
        try:
            authorize_view = view_callable.as_view()
        except AttributeError:
            # if it appears not to be CBV treat it like FBV
            authorize_view = view_callable

        params = oauth_request.get_normalized_parameters()
        # set the oauth flag
        request.session['oauth'] = request_token.key
        response = authorize_view(
            request, request_token, request_token.get_callback_url(), params)

    return response


@csrf_exempt
def access_token(request):
    oauth_request = get_oauth_request(request)
    if oauth_request is None:
        return HttpResponseBadRequest('Invalid request parameters.')

    # Consumer
    try:
        consumer = store.get_consumer(
            request, oauth_request, oauth_request['oauth_consumer_key'])
    except InvalidConsumerError:
        return HttpResponseBadRequest('Invalid consumer.')

    is_xauth = is_xauth_request(oauth_request)

    if not is_xauth:

        # Check Parameters
        missing_params = require_params(
            oauth_request, ('oauth_token', 'oauth_verifier'))
        if missing_params is not None:
            return missing_params

        # Check Request Token
        try:
            request_token = store.get_request_token(
                request, oauth_request, oauth_request['oauth_token'])
        except InvalidTokenError:
            return HttpResponse('Invalid request token: %s' % oauth_request['oauth_token'], status=401)
        if not request_token.is_approved:
            return HttpResponse('Request Token not approved by the user.', status=401)

        # Verify Signature
        if not verify_oauth_request(request, oauth_request, consumer, request_token):
            return HttpResponseBadRequest('Could not verify OAuth request.')

        # Check Verifier
        if oauth_request.get('oauth_verifier', None) != request_token.verifier:
            return HttpResponseBadRequest('Invalid OAuth verifier.')

    else:  # xAuth

        # Check Parameters
        missing_params = require_params(
            oauth_request, ('x_auth_username', 'x_auth_password', 'x_auth_mode'))
        if missing_params is not None:
            return missing_params

        # Check if Consumer allows xAuth
        if not consumer.xauth_allowed:
            return HttpResponseBadRequest('xAuth not allowed for this method')

        # Check Signature
        if not verify_oauth_request(request, oauth_request, consumer):
            return HttpResponseBadRequest('Could not verify xAuth request.')

        user = authenticate(
            x_auth_username=oauth_request.get_parameter('x_auth_username'),
            x_auth_password=oauth_request.get_parameter('x_auth_password'),
            x_auth_mode=oauth_request.get_parameter('x_auth_mode')
        )

        if not user:
            return HttpResponseBadRequest('xAuth username or password is not valid')
        else:
            request.user = user

        # Handle Request Token
        try:
            # request_token = store.create_request_token(request, oauth_request, consumer, oauth_request.get('oauth_callback'))
            request_token = store.create_request_token(
                request, oauth_request, consumer, OUT_OF_BAND)
            request_token = store.authorize_request_token(
                request, oauth_request, request_token)
        except oauth.Error as err:
            return send_oauth_error('https' if request.is_secure() else 'http',
                get_current_site(request).domain, err)

    access_token = store.create_access_token(
        request, oauth_request, consumer, request_token)

    ret = urlencode({
        'oauth_token': access_token.key,
        'oauth_token_secret': access_token.secret
    })
    return HttpResponse(ret, content_type='application/x-www-form-urlencoded')

# LRS CHANGE - ADDED OUR REAL VIEWS


@login_required(login_url="/accounts/login")
def authorize_client(request, token=None, callback=None, params=None, form=None):
    if not form:
        form = AuthorizeRequestTokenForm(initial={'scopes': token.scope_to_list(),
                                                  'obj_id': token.pk})
    d = {}
    d['oauth_scopes'] = settings.OAUTH_SCOPES
    d['scopes'] = json.dumps(token.scope_to_list())
    d['form'] = form
    d['name'] = token.consumer.name
    d['description'] = token.consumer.description
    d['params'] = params
    d['oauth_token'] = token.key
    return render(request, 'oauth_authorize_client.html', d)


@login_required(login_url="/accounts/login")
def callback_view(request, **args):
    d = {}
    if 'error' in args:
        d['error'] = args['error']

    try:
        oauth_token = Token.objects.get(key=args['oauth_token'])
    except AttributeError as e:
        send_oauth_error('https' if request.is_secure() else 'http',
            get_current_site(request).domain, e)
    except Token.DoesNotExist as e:
        send_oauth_error('https' if request.is_secure() else 'http',
            get_current_site(request).domain, e)
    d['verifier'] = oauth_token.verifier
    return render(request, 'oauth_verifier_pin.html', d)
