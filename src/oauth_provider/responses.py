# -*- coding: utf-8 -*-
from django.utils.translation import ugettext as _
from django.http import HttpResponseBadRequest

import oauth2 as oauth

from oauth_provider.utils import send_oauth_error


INVALID_CONSUMER_RESPONSE = HttpResponseBadRequest('Invalid Consumer.')

def invalid_params_response(scheme, domain):
	send_oauth_error(
    	oauth.Error(scheme, domain, _('Invalid request parameters.')))

def invalid_scope_response(scheme, domain):
	send_oauth_error(scheme, domain,
		oauth.Error(_('You are not allowed to access this resource.')))

def could_not_verify_oauth_request_response(scheme, domain):
	send_oauth_error(scheme, domain,
		oauth.Error(_('Could not verify OAuth request.')))
