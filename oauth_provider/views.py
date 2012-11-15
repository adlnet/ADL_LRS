from urllib import urlencode

import oauth2 as oauth
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext as _
from django.core.urlresolvers import get_callable

from oauth_provider.decorators import oauth_required
from oauth_provider.forms import AuthorizeRequestTokenForm
from oauth_provider.store import store, InvalidConsumerError, InvalidTokenError
from oauth_provider.utils import verify_oauth_request, get_oauth_request, require_params, send_oauth_error
from oauth_provider.consts import OUT_OF_BAND

OAUTH_AUTHORIZE_VIEW = 'OAUTH_AUTHORIZE_VIEW'
OAUTH_CALLBACK_VIEW = 'OAUTH_CALLBACK_VIEW'
INVALID_PARAMS_RESPONSE = send_oauth_error(oauth.Error(
                                            _('Invalid request parameters.')))

@csrf_exempt
def request_token(request):
    oauth_request = get_oauth_request(request)
    if oauth_request is None:
        return INVALID_PARAMS_RESPONSE

    missing_params = require_params(oauth_request, ('oauth_callback',))
    if missing_params is not None:
        return missing_params

    try:
        consumer = store.get_consumer(request, oauth_request, oauth_request['oauth_consumer_key'])
    except InvalidConsumerError:
        return HttpResponseBadRequest('Invalid Consumer.')

    if not verify_oauth_request(request, oauth_request, consumer):
        return HttpResponseBadRequest('Could not verify OAuth request.')

    try:
        request_token = store.create_request_token(request, oauth_request, consumer, oauth_request['oauth_callback'])
    except oauth.Error, err:
        return send_oauth_error(err)

    ret = urlencode({
        'oauth_token': request_token.key,
        'oauth_token_secret': request_token.secret,
        'oauth_callback_confirmed': 'true'
    })
    return HttpResponse(ret, content_type='application/x-www-form-urlencoded')


@login_required
def user_authorization(request, form_class=AuthorizeRequestTokenForm):
    if 'oauth_token' not in request.REQUEST:
        return HttpResponseBadRequest('No request token specified.')

    oauth_request = get_oauth_request(request)

    try:
        request_token = store.get_request_token(request, oauth_request, request.REQUEST['oauth_token'])
    except InvalidTokenError:
        return HttpResponseBadRequest('Invalid request token.')

    consumer = store.get_consumer_for_request_token(request, oauth_request, request_token)

    if request.method == 'POST':
        form = form_class(request.POST)
        if request.session.get('oauth', '') == request_token.key and form.is_valid():
            request.session['oauth'] = ''
            if form.cleaned_data['authorize_access']:
                request_token = store.authorize_request_token(request, oauth_request, request_token)
                args = { 'oauth_token': request_token.key }
            else:
                args = { 'error': _('Access not granted by user.') }
            if request_token.callback is not None and request_token.callback != OUT_OF_BAND:
                response = HttpResponseRedirect(request_token.get_callback_url(args))
            else:
                # try to get custom callback view
                callback_view_str = getattr(settings, OAUTH_CALLBACK_VIEW, 
                                    'oauth_provider.views.fake_callback_view')
                try:
                    callback_view = get_callable(callback_view_str)
                except AttributeError:
                    raise Exception, "%s view doesn't exist." % callback_view_str
                response = callback_view(request, **args)
        else:
            response = send_oauth_error(oauth.Error(_('Action not allowed.')))
    else:
        # try to get custom authorize view
        authorize_view_str = getattr(settings, OAUTH_AUTHORIZE_VIEW, 
                                    'oauth_provider.views.fake_authorize_view')
        try:
            authorize_view = get_callable(authorize_view_str)
        except AttributeError:
            raise Exception, "%s view doesn't exist." % authorize_view_str
        params = oauth_request.get_normalized_parameters()
        # set the oauth flag
        request.session['oauth'] = request_token.key
        response = authorize_view(request, request_token, request_token.get_callback_url(), params)
        
    return response


@csrf_exempt
def access_token(request):
    oauth_request = get_oauth_request(request)
    if oauth_request is None:
        return INVALID_PARAMS_RESPONSE

    missing_params = require_params(oauth_request, ('oauth_token', 'oauth_verifier'))
    if missing_params is not None:
        return missing_params

    try:
        request_token = store.get_request_token(request, oauth_request, oauth_request['oauth_token'])
    except InvalidTokenError:
        return HttpResponseBadRequest('Invalid request token.')
    try:
        consumer = store.get_consumer(request, oauth_request, oauth_request['oauth_consumer_key'])
    except InvalidConsumerError:
        return HttpResponseBadRequest('Invalid consumer.')

    if not verify_oauth_request(request, oauth_request, consumer, request_token):
        return HttpResponseBadRequest('Could not verify OAuth request.')

    if oauth_request.get('oauth_verifier', None) != request_token.verifier:
        return HttpResponseBadRequest('Invalid OAuth verifier.')

    if not request_token.is_approved:
        return HttpResponseBadRequest('Request Token not approved by the user.')

    access_token = store.create_access_token(request, oauth_request, consumer, request_token)

    ret = urlencode({
        'oauth_token': access_token.key,
        'oauth_token_secret': access_token.secret
    })
    return HttpResponse(ret, content_type='application/x-www-form-urlencoded')

@oauth_required
def protected_resource_example(request):
    """
    Test view for accessing a Protected Resource.
    """
    return HttpResponse('Protected Resource access!')

@login_required
def fake_authorize_view(request, token, callback, params):
    """
    Fake view for tests. It must return an ``HttpResponse``.
    
    You need to define your own in ``settings.OAUTH_AUTHORIZE_VIEW``.
    """
    return HttpResponse('Fake authorize view for %s with params: %s.' % (token.consumer.name, params))

def fake_callback_view(request, **args):
    """
    Fake view for tests. It must return an ``HttpResponse``.
    
    You can define your own in ``settings.OAUTH_CALLBACK_VIEW``.
    """
    return HttpResponse('Fake callback view.')
