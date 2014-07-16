# -*- coding: utf-8 -*-
from django.utils.translation import ugettext as _
from django.http import HttpResponseBadRequest

import oauth2 as oauth

from oauth_provider.utils import send_oauth_error

INVALID_PARAMS_RESPONSE = send_oauth_error(oauth.Error(_('Invalid request parameters.')))
INVALID_CONSUMER_RESPONSE = HttpResponseBadRequest('Invalid Consumer.')
INVALID_SCOPE_RESPONSE = send_oauth_error(oauth.Error(_('You are not allowed to access this resource.')))
COULD_NOT_VERIFY_OAUTH_REQUEST_RESPONSE = send_oauth_error(oauth.Error(_('Could not verify OAuth request.')))
