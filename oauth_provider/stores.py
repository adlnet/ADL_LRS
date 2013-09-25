from urlparse import urlparse

from oauth.oauth import OAuthDataStore, OAuthError, escape

from django.conf import settings

from vendor.xapi.lrs.models import Nonce, Token, Consumer, generate_random
from consts import VERIFIER_SIZE, MAX_URL_LENGTH, OUT_OF_BAND

OAUTH_BLACKLISTED_HOSTNAMES = getattr(settings, 'OAUTH_BLACKLISTED_HOSTNAMES', [])
OAUTH_SCOPES = ["statements/write", "statements/read/mine", "statements/read", "state", "define",
                "profile", "all/read", "all"]

class DataStore(OAuthDataStore):
    """Layer between Python OAuth and Django database."""
    def __init__(self, oauth_request):
        self.signature = oauth_request.parameters.get('oauth_signature', None)
        self.timestamp = oauth_request.parameters.get('oauth_timestamp', None)
        # tom c 
        # changed default scope to s/w & s/r/m
        self.scope = oauth_request.parameters.get('scope', None)

    def lookup_consumer(self, key):
        try:
            self.consumer = Consumer.objects.get(key=key)
            return self.consumer
        except Consumer.DoesNotExist:
            return None

    def lookup_token(self, token_type, token):
        if token_type == 'request':
            token_type = Token.REQUEST
        elif token_type == 'access':
            token_type = Token.ACCESS
        try:
            self.request_token = Token.objects.get(key=token, 
                                                   token_type=token_type)
            return self.request_token
        except Token.DoesNotExist:
            return None

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        if oauth_token is None:
            return None
        nonce, created = Nonce.objects.get_or_create(consumer_key=oauth_consumer.key, 
                                                     token_key=oauth_token.key,
                                                     key=nonce)
        if created:
            return None
        else:
            return nonce.key

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        if oauth_consumer.key != self.consumer.key:
            raise OAuthError('Consumer key does not match.')
        
        # OAuth 1.0a: if there is a callback, check its validity
        callback = None
        # tom c changed... call back confirmed is supposed to be true
        # callback_confirmed = False
        callback_confirmed = True
        
        if oauth_callback:
            if oauth_callback != OUT_OF_BAND:
                if check_valid_callback(oauth_callback):
                    callback = oauth_callback
                else:
                    # tom c
                    callback_confirmed = False
                    raise OAuthError('Invalid callback URL.')

        # tom c - changed... Resource used to represent a specific scope
        # with xapi scopes could be many.. using resource as a holder of
        # many scopes
        if self.scope:
            scope = self.scope
        else:
            scope = self.consumer.default_scopes
                
        # lou w - Make sure a valid scope(s) is supplied
        scope_list = scope.split(",")
        for x in scope_list:
            if not x in OAUTH_SCOPES:
                raise OAuthError('Resource %s is not allowed.' % escape(self.scope))

        # lou w - save as scope instead of resource
        self.request_token = Token.objects.create_token(consumer=self.consumer,
                                                        token_type=Token.REQUEST,
                                                        timestamp=self.timestamp,
                                                        scope=scope,
                                                        callback=callback,
                                                        callback_confirmed=callback_confirmed)
        
        return self.request_token
        

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        # lou w - save scope from token scope instead of resource
        if oauth_consumer.key == self.consumer.key \
        and oauth_token.key == self.request_token.key \
        and self.request_token.is_approved:
            # OAuth 1.0a: if there is a callback confirmed, check the verifier
            if (self.request_token.callback_confirmed \
            and oauth_verifier == self.request_token.verifier) \
            or not self.request_token.callback_confirmed:
                self.access_token = Token.objects.create_token(consumer=self.consumer,
                                                               token_type=Token.ACCESS,
                                                               timestamp=self.timestamp,
                                                               user=self.request_token.user,
                                                               scope=self.request_token.scope)
                # tom c says access tokens start as approved
                self.access_token.is_approved = True
                self.access_token.save()
                return self.access_token
        raise OAuthError('Consumer key or token key does not match. ' \
                        +'Make sure your request token is approved. ' \
                        +'Check your verifier too if you use OAuth 1.0a.')

    def authorize_request_token(self, oauth_token, user):
        if oauth_token.key == self.request_token.key:
            # authorize the request token in the store
            self.request_token.is_approved = True
            self.request_token.save()
            # OAuth 1.0a: if there is a callback confirmed, we must set a verifier
            if self.request_token.callback_confirmed:
                self.request_token.verifier = generate_random(VERIFIER_SIZE)
            
            self.request_token.user = user
            self.request_token.save()
            return self.request_token
        raise OAuthError('Token key or lrs_auth_id does not match.')


def check_valid_callback(callback):
    """
    Checks the size and nature of the callback.
    """
    callback_url = urlparse(callback)
    return (callback_url.scheme
            and callback_url.hostname not in OAUTH_BLACKLISTED_HOSTNAMES
            and len(callback) < MAX_URL_LENGTH)
