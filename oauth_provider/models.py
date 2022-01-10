import uuid
import urllib.request, urllib.parse, urllib.error
import urllib.parse
from datetime import datetime
from time import time
import oauth2 as oauth
from Crypto.PublicKey import RSA
from django.db import models

from oauth_provider.compat import AUTH_USER_MODEL, get_random_string
from oauth_provider.managers import TokenManager
from oauth_provider.consts import KEY_SIZE, RSA_SECRET_SIZE, CONSUMER_KEY_SIZE, CONSUMER_STATES,\
    PENDING, VERIFIER_SIZE, MAX_URL_LENGTH, OUT_OF_BAND, REGULAR_SECRET_SIZE
from oauth_provider.utils import check_valid_callback


class Nonce(models.Model):
    token_key = models.CharField(max_length=KEY_SIZE)
    consumer_key = models.CharField(max_length=CONSUMER_KEY_SIZE)
    key = models.CharField(max_length=255)
    timestamp = models.PositiveIntegerField(db_index=True)

    def __unicode__(self):
        return "Nonce %s for %s" % (self.key, self.consumer_key)

# LRS CHANGE - NOT NEEDED
# class Scope(models.Model):
#     name = models.CharField(max_length=255)
#     url = models.TextField(max_length=MAX_URL_LENGTH)
#     is_readonly = models.BooleanField(default=True)

#     def __unicode__(self):
#         return u"Resource %s with url %s" % (self.name, self.url)

# LRS CHANGE - NOT NEEDED
# class Resource(Scope):

#     def __init__(self, *args, **kwargs):
#         warnings.warn("oauth_provider.Resource model is deprecated, use oauth_provider.Scope instead", DeprecationWarning)
#         super(Resource, self).__init__(*args, **kwargs)

#     class Meta:
#         proxy = True


class Consumer(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # LRS CHANGE - ADDED DEFAULT SCOPES FOR CONSUMER WHEN FIRST REGISTERED
    # default_scopes = models.CharField(max_length=100, default="statements/write statements/read/mine")

    key = models.CharField(max_length=CONSUMER_KEY_SIZE)
    secret = models.CharField(max_length=RSA_SECRET_SIZE, blank=True)
    rsa_signature = models.BooleanField(default=False)

    status = models.SmallIntegerField(choices=CONSUMER_STATES, default=PENDING)
    user = models.ForeignKey(AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    xauth_allowed = models.BooleanField("Allow xAuth", default=False)

    def __unicode__(self):
        return "Consumer %s with key %s" % (self.name, self.key)

    def generate_random_codes(self):
        """
        Used to generate random key/secret pairings.
        Use this after you've added the other data in place of save().
        """
        self.key = uuid.uuid4().hex
        # LRS CHANGE - KEPT THE SECRET KEY AT 16 LIKE BEFORE (WHEN NOT USING
        # RSA)
        if not self.rsa_signature:
            self.secret = get_random_string(length=REGULAR_SECRET_SIZE)
        self.save()

    def generate_rsa_key(self):
        if not self.secret or len(self.secret) == REGULAR_SECRET_SIZE:
            return None
        return RSA.importKey(self.secret)


class Token(models.Model):
    REQUEST = 1
    ACCESS = 2
    TOKEN_TYPES = ((REQUEST, 'Request'), (ACCESS, 'Access'))

    key = models.CharField(max_length=KEY_SIZE, null=True, blank=True)
    secret = models.CharField(
        max_length=RSA_SECRET_SIZE, null=True, blank=True)
    token_type = models.SmallIntegerField(choices=TOKEN_TYPES)
    timestamp = models.IntegerField(default=int(time()))
    is_approved = models.BooleanField(default=False)

    user = models.ForeignKey(AUTH_USER_MODEL, null=True,
                             blank=True, related_name='tokens', on_delete=models.CASCADE)
    consumer = models.ForeignKey(Consumer, on_delete=models.CASCADE)
    # LRS CHANGE - LRS SCOPES AREN'T RESOURCES
    # scope = models.ForeignKey(Scope, null=True, blank=True)
    scope = models.CharField(
        max_length=100, default="statements/write statements/read/mine")

    @property
    def resource(self):
        return self.scope

    @resource.setter
    def resource(self, value):
        self.scope = value

    # OAuth 1.0a stuff
    verifier = models.CharField(max_length=VERIFIER_SIZE)
    callback = models.CharField(
        max_length=MAX_URL_LENGTH, null=True, blank=True)
    callback_confirmed = models.BooleanField(default=False)

    objects = TokenManager()

    def __unicode__(self):
        return "%s Token %s for %s" % (self.get_token_type_display(), self.key, self.consumer)

    def to_string(self, only_key=False):
        token_dict = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
            'oauth_callback_confirmed': self.callback_confirmed and 'true' or 'error'
        }
        if self.verifier:
            token_dict['oauth_verifier'] = self.verifier

        if only_key:
            del token_dict['oauth_token_secret']
            del token_dict['oauth_callback_confirmed']

        return urllib.parse.urlencode(token_dict)

    def generate_random_codes(self):
        """
        Used to generate random key/secret pairings.
        Use this after you've added the other data in place of save().
        """
        self.key = uuid.uuid4().hex
        if not self.consumer.rsa_signature:
            self.secret = get_random_string(length=REGULAR_SECRET_SIZE)
        self.save()

    def get_callback_url(self, args=None):
        """
        OAuth 1.0a, append the oauth_verifier.
        """
        if self.callback and self.verifier:
            parts = urllib.parse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier

            # workaround for non-http scheme urlparse problem in py2.6 (issue
            # #2)
            if "?" in path:
                query = "%s&%s" % (path.split("?")[-1], query)
                path = "?".join(path[:-1])

            if args is not None:
                query += "&%s" % urllib.parse.urlencode(args)
            return urllib.parse.urlunparse((scheme, netloc, path, params,
                                        query, fragment))
        args = args is not None and "?%s" % urllib.parse.urlencode(args) or ""
        return self.callback and self.callback + args

    def set_callback(self, callback):
        if callback != OUT_OF_BAND:  # out of band, says "we can't do this!"
            if check_valid_callback(callback):
                self.callback = callback
                self.callback_confirmed = True
                self.save()
            else:
                raise oauth.Error('Invalid callback URL.')

    # LRS CHANGE - ADDED HELPER FUNCTIONS
    def scope_to_list(self):
        return self.scope.split(" ")

    def timestamp_asdatetime(self):
        return datetime.fromtimestamp(self.timestamp)

    def key_partial(self):
        return self.key[:10]
