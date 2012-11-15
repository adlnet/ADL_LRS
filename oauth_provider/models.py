import uuid
import urllib
import urlparse
from time import time
import oauth2 as oauth

from django.db import models
from django.contrib.auth.models import User

from oauth_provider.managers import TokenManager
from oauth_provider.consts import KEY_SIZE, SECRET_SIZE, CONSUMER_KEY_SIZE, CONSUMER_STATES,\
                   PENDING, VERIFIER_SIZE, MAX_URL_LENGTH, OUT_OF_BAND
from oauth_provider.utils import check_valid_callback

generate_random = User.objects.make_random_password

class Nonce(models.Model):
    token_key = models.CharField(max_length=KEY_SIZE)
    consumer_key = models.CharField(max_length=CONSUMER_KEY_SIZE)
    key = models.CharField(max_length=255)
    
    def __unicode__(self):
        return u"Nonce %s for %s" % (self.key, self.consumer_key)


class Resource(models.Model):
    name = models.CharField(max_length=255)
    url = models.TextField(max_length=MAX_URL_LENGTH)
    is_readonly = models.BooleanField(default=True)

    def __unicode__(self):
        return u"Resource %s with url %s" % (self.name, self.url)


class Consumer(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    key = models.CharField(max_length=CONSUMER_KEY_SIZE)
    secret = models.CharField(max_length=SECRET_SIZE, blank=True)

    status = models.SmallIntegerField(choices=CONSUMER_STATES, default=PENDING)
    user = models.ForeignKey(User, null=True, blank=True)
        
    def __unicode__(self):
        return u"Consumer %s with key %s" % (self.name, self.key)

    def generate_random_codes(self):
        """
        Used to generate random key/secret pairings.
        Use this after you've added the other data in place of save().
        """
        self.key = uuid.uuid4().hex
        self.secret = generate_random(length=SECRET_SIZE)
        self.save()


class Token(models.Model):
    REQUEST = 1
    ACCESS = 2
    TOKEN_TYPES = ((REQUEST, u'Request'), (ACCESS, u'Access'))
    
    key = models.CharField(max_length=KEY_SIZE, null=True, blank=True)
    secret = models.CharField(max_length=SECRET_SIZE, null=True, blank=True)
    token_type = models.SmallIntegerField(choices=TOKEN_TYPES)
    timestamp = models.IntegerField(default=long(time()))
    is_approved = models.BooleanField(default=False)
    
    user = models.ForeignKey(User, null=True, blank=True, related_name='tokens')
    consumer = models.ForeignKey(Consumer)
    resource = models.ForeignKey(Resource)
    
    ## OAuth 1.0a stuff
    verifier = models.CharField(max_length=VERIFIER_SIZE)
    callback = models.CharField(max_length=MAX_URL_LENGTH, null=True, blank=True)
    callback_confirmed = models.BooleanField(default=False)
    
    objects = TokenManager()
    
    def __unicode__(self):
        return u"%s Token %s for %s" % (self.get_token_type_display(), self.key, self.consumer)

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

        return urllib.urlencode(token_dict)

    def generate_random_codes(self):
        """
        Used to generate random key/secret pairings. 
        Use this after you've added the other data in place of save(). 
        """
        self.key = uuid.uuid4().hex
        self.secret = generate_random(length=SECRET_SIZE)
        self.save()

    def get_callback_url(self, args=None):
        """
        OAuth 1.0a, append the oauth_verifier.
        """
        if self.callback and self.verifier:
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            if args is not None:
                query += "&%s" % urllib.urlencode(args)
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        args = args is not None and "?%s" % urllib.urlencode(args) or ""
        return self.callback + args

    def set_callback(self, callback):
        if callback != OUT_OF_BAND: # out of band, says "we can't do this!"
            if check_valid_callback(callback):
                self.callback = callback
                self.callback_confirmed = True
                self.save()
            else:
                raise oauth.Error('Invalid callback URL.')
        
