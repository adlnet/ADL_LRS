from django.utils.translation import ugettext_lazy as _
from django.conf import settings

KEY_SIZE = getattr(settings, 'OAUTH_PROVIDER_KEY_SIZE', 32)
SECRET_SIZE = getattr(settings, 'OAUTH_PROVIDER_SECRET_SIZE', 16)
VERIFIER_SIZE = getattr(settings, 'OAUTH_PROVIDER_VERIFIER_SIZE', 10)
CONSUMER_KEY_SIZE = getattr(settings, 'OAUTH_PROVIDER_CONSUMER_KEY_SIZE', 256)
MAX_URL_LENGTH = 2083 # http://www.boutell.com/newfaq/misc/urllength.html

PENDING = 1
ACCEPTED = 2
CANCELED = 3
REJECTED = 4

CONSUMER_STATES = (
    (PENDING,  _('Pending')),
    (ACCEPTED, _('Accepted')),
    (CANCELED, _('Canceled')),
    (REJECTED, _('Rejected')),
)

PARAMETERS_NAMES = ('consumer_key', 'token', 'signature',
                    'signature_method', 'timestamp', 'nonce')
OAUTH_PARAMETERS_NAMES = ['oauth_'+s for s in PARAMETERS_NAMES]

OUT_OF_BAND = 'oob'
