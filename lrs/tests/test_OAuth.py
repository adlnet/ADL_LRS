import uuid
import json
import urllib.request, urllib.parse, urllib.error
import os
import base64
import time
import string
import random
import oauth2 as oauth
from Crypto.PublicKey import RSA

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase

from ..models import Activity, Agent
from adl_lrs.views import register, regclient

from oauth_provider.models import Consumer, Token, Nonce
from oauth_provider.utils import SignatureMethod_RSA_SHA1

# Django client uses testserver
TEST_SERVER = 'http://testserver'
INITIATE_ENDPOINT = TEST_SERVER + "/XAPI/OAuth/initiate"
AUTHORIZATION_ENDPOINT = TEST_SERVER + "/XAPI/OAuth/authorize"
TOKEN_ENDPOINT = TEST_SERVER + "/XAPI/OAuth/token"


class OAuthTests(TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n%s" % __name__)
        super(OAuthTests, cls).setUpClass()

    def setUp(self):
        if not settings.OAUTH_ENABLED:
            settings.OAUTH_ENABLED = True

        # Create a user
        form = {"username": "jane", "email": "jane@example.com",
                "password": "toto", "password2": "toto"}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)
        self.user = User.objects.get(username='jane')

        # Register a consumer
        self.name = "test jane client"
        self.desc = "test jane client desc"
        form = {"name": self.name, "description": self.desc}
        self.client.post(reverse(regclient), form)
        self.consumer = Consumer.objects.get(name=self.name)

        self.name2jane = "test jane client2"
        self.desc2jane = "test jane client desc2"
        form2jane = {"name": self.name2jane, "description": self.desc2jane}
        self.client.post(reverse(regclient), form2jane)
        self.consumer2jane = Consumer.objects.get(name=self.name2jane)

        self.client.logout()
        self.jane_auth = "Basic %s" % base64.b64encode(
            "%s:%s" % ('jane', 'toto'))

        # Create a user
        self.user2 = User.objects.create_user(
            'dick', 'dick@example.com', 'lassie')
        self.client.login(username='dick', password='lassie')

        # Register a client
        self.name2 = "test client2"
        self.desc2 = "test desc2"
        form2 = {"name": self.name2, "description": self.desc2}
        self.client.post(reverse(regclient), form2)
        self.consumer2 = Consumer.objects.get(name=self.name2)
        self.client.logout()
        self.dick_auth = "Basic %s" % base64.b64encode(
            "%s:%s" % ('dick', 'lassie'))

    def tearDown(self):
        if settings.OAUTH_ENABLED:
            settings.OAUTH_ENABLED = False
        # Delete everything
        Token.objects.all().delete()
        Consumer.objects.all().delete()
        Nonce.objects.all().delete()
        User.objects.all().delete()

        attach_folder_path = os.path.join(
            settings.MEDIA_ROOT, "activity_state")
        for the_file in os.listdir(attach_folder_path):
            file_path = os.path.join(attach_folder_path, the_file)
            try:
                os.unlink(file_path)
            except Exception as e:
                raise e

    def oauth_handshake(self, scope=True, scope_type=None, parameters=None, param_type='qs', change_scope=[],
                        request_nonce='', access_nonce='', resource_nonce='', consumer=None):

        # ============= INITIATE =============
        if not request_nonce:
            request_nonce = ''.join(random.choice(
                string.ascii_uppercase + string.digits) for _ in range(6))

        if not consumer:
            consumer = self.consumer

        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"%s\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/access_token_ready\"" % (
                consumer.key, str(int(time.time())), request_nonce)

        # Add non oauth parameters appropriately
        request_token_params = {}
        if parameters:
            request_token_params = parameters

        # Set scope
        if scope:
            if scope_type:
                request_token_params['scope'] = scope_type
            else:
                request_token_params['scope'] = "all"

        # Add non oauth params in query string or form
        if param_type == 'qs':
            request_token_path = "%s?%s" % (
                INITIATE_ENDPOINT, urllib.parse.urlencode(request_token_params))
        else:
            request_token_path = INITIATE_ENDPOINT

        # Make the params into a dict to pass into from_consumer_and_token
        oauth_header_request_token_params_list = oauth_header_request_token_params.split(
            ",")
        oauth_header_request_token_params_dict = {}
        for p in oauth_header_request_token_params_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # Make oauth request depending on where the parameters are
        if param_type == 'qs':
            oauth_request = oauth.Request.from_consumer_and_token(consumer, token=None, http_method='GET',
                                                                  http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        else:
            oauth_request = oauth.Request.from_consumer_and_token(consumer, token=None, http_method='POST',
                                                                  http_url=request_token_path, parameters=dict(list(oauth_header_request_token_params_dict.items()) + list(request_token_params.items())))

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        # Send request depending on the parameters
        if param_type == 'qs':
            request_resp = self.client.get(
                request_token_path, Authorization=oauth_header_request_token_params)
        else:
            request_resp = self.client.post(request_token_path, Authorization=oauth_header_request_token_params, data=request_token_params,
                                            content_type="application/x-www-form-urlencoded")

        # Get request token (will be only token for that user)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token_secret = request_resp.content.split('&')[0].split('=')[1]
        request_token = Token.objects.get(secret=token_secret)
        # ============= END INITIATE =============

        # ============= AUTHORIZE =============
        # Create authorize path, must have oauth_token param
        authorize_param = {'oauth_token': request_token.key}
        authorize_path = "%s?%s" % (
            AUTHORIZATION_ENDPOINT, urllib.parse.urlencode(authorize_param))

        # Try to hit auth path, made to login
        auth_resp = self.client.get(authorize_path)
        self.assertEqual(auth_resp.status_code, 302)

        self.assertIn(
            '/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(request_token.key, auth_resp['Location'])
        self.client.login(username='jane', password='toto')
        self.assertEqual(request_token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path)
        # Show return/display OAuth authorized view
        self.assertEqual(auth_resp.status_code, 200)

        # Get the form, set required fields
        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = request_token.key

        # Change scope if wanted
        if change_scope:
            data['scope'] = change_scope

        # Post data back to auth endpoint - should redirect to callback_url we
        # set in oauth headers with request token
        auth_post = self.client.post(AUTHORIZATION_ENDPOINT, data)
        self.assertEqual(auth_post.status_code, 302)
        # Check if oauth_verifier and oauth_token are returned
        self.assertIn(
            'http://example.com/access_token_ready?oauth_verifier=', auth_post['Location'])
        self.assertIn('oauth_token=', auth_post['Location'])
        # Get token again just to make sure
        token_key = auth_post['Location'].split(
            '?')[1].split('&')[1].split('=')[1]
        request_token_after_auth = Token.objects.get(key=token_key)
        self.assertIn(request_token_after_auth.key, auth_post['Location'])
        self.assertEqual(request_token_after_auth.is_approved, True)
        #  ============= END AUTHORIZE =============

        # ============= ACCESS TOKEN =============
        if not access_nonce:
            access_nonce = "access_nonce"

        # Set verifier in access_token params and create new oauth request
        oauth_header_access_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"%s\","\
            "oauth_version=\"1.0\","\
            "oauth_verifier=\"%s\"" % (consumer.key, request_token_after_auth.key, str(
                int(time.time())), access_nonce, request_token_after_auth.verifier)

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_access_token_params.split(",")
        oauth_header_access_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_access_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_access_params_dict['OAuth realm']
        oauth_request = oauth.Request.from_token_and_callback(request_token_after_auth, http_method='GET',
                                                              http_url=TOKEN_ENDPOINT, parameters=oauth_header_access_params_dict)

        # Create signature and add it to the headers
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, consumer, request_token_after_auth)
        oauth_header_access_token_params += ',oauth_signature="%s"' % signature

        # Get access token
        access_resp = self.client.get(
            TOKEN_ENDPOINT, Authorization=oauth_header_access_token_params)
        self.assertEqual(access_resp.status_code, 200)
        content = access_resp.content.split('&')
        access_token_secret = content[0].split('=')[1]
        access_token_key = content[1].split('=')[1]
        access_token = Token.objects.get(
            secret=access_token_secret, key=access_token_key)
        #  ============= END ACCESS TOKEN =============

        if not resource_nonce:
            resource_nonce = "resource_nonce"
        # Set oauth headers user will use when hitting xapi endpoing and access
        # token
        oauth_header_resource_params = "OAuth realm=\"test\", "\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"%s\","\
            "oauth_version=\"1.0\"" % (consumer.key, access_token.key, str(
                int(time.time())), resource_nonce)

        self.client.logout()
        return oauth_header_resource_params, access_token

    def oauth_handshake2(self, scope=True, scope_type=None, parameters=None, param_type='qs', change_scope=[],
                         request_nonce='', access_nonce='', resource_nonce=''):

        # ============= INITIATE =============
        if not request_nonce:
            request_nonce = "request_nonce2"

        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"%s\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/access_token_ready\"" % (
                self.consumer2.key, str(int(time.time())), request_nonce)

        # Add non oauth parameters appropriately
        request_token_params = {}
        if parameters:
            request_token_params = parameters

        if scope:
            if scope_type:
                request_token_params['scope'] = scope_type
            else:
                request_token_params['scope'] = "all"

        if param_type == 'qs':
            request_token_path = "%s?%s" % (
                INITIATE_ENDPOINT, urllib.parse.urlencode(request_token_params))
        else:
            request_token_path = INITIATE_ENDPOINT

        # Make the params into a dict to pass into from_consumer_and_token
        oauth_header_request_token_params_list = oauth_header_request_token_params.split(
            ",")
        oauth_header_request_token_params_dict = {}
        for p in oauth_header_request_token_params_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        if param_type == 'qs':
            oauth_request = oauth.Request.from_consumer_and_token(self.consumer2, token=None, http_method='GET',
                                                                  http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        else:
            oauth_request = oauth.Request.from_consumer_and_token(self.consumer2, token=None, http_method='POST',
                                                                  http_url=request_token_path, parameters=dict(list(oauth_header_request_token_params_dict.items()) + list(request_token_params.items())))

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer2, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        if param_type == 'qs':
            request_resp = self.client.get(
                request_token_path, Authorization=oauth_header_request_token_params)
        else:
            request_resp = self.client.post(request_token_path, Authorization=oauth_header_request_token_params, data=request_token_params,
                                            content_type="application/x-www-form-urlencoded")

        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        request_token = Token.objects.get(consumer=self.consumer2)
        # ============= END INITIATE =============

        # ============= AUTHORIZE =============
        authorize_param = {'oauth_token': request_token.key}
        authorize_path = "%s?%s" % (
            AUTHORIZATION_ENDPOINT, urllib.parse.urlencode(authorize_param))

        auth_resp = self.client.get(authorize_path)
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn(
            '/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(request_token.key, auth_resp['Location'])
        self.client.login(username='dick', password='lassie')
        self.assertEqual(request_token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path)
        # Show return/display OAuth authorized view
        self.assertEqual(auth_resp.status_code, 200)

        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = request_token.key

        # Change scope if wanted
        if change_scope:
            data['scope'] = change_scope

        auth_post = self.client.post(AUTHORIZATION_ENDPOINT, data)
        self.assertEqual(auth_post.status_code, 302)
        # Check if oauth_verifier and oauth_token are returned
        self.assertIn(
            'http://example.com/access_token_ready?oauth_verifier=', auth_post['Location'])
        self.assertIn('oauth_token=', auth_post['Location'])
        request_token_after_auth = Token.objects.get(consumer=self.consumer2)
        self.assertIn(request_token_after_auth.key, auth_post['Location'])
        self.assertEqual(request_token_after_auth.is_approved, True)
        #  ============= END AUTHORIZE =============

        # ============= ACCESS TOKEN =============
        if not access_nonce:
            access_nonce = "access_nonce2"

        oauth_header_access_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"%s\","\
            "oauth_version=\"1.0\","\
            "oauth_verifier=\"%s\"" % (self.consumer2.key, request_token_after_auth.key, str(
                int(time.time())), access_nonce, request_token_after_auth.verifier)

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_access_token_params.split(",")
        oauth_header_access_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_access_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_access_params_dict['OAuth realm']
        oauth_request = oauth.Request.from_token_and_callback(request_token_after_auth, http_method='GET',
                                                              http_url=TOKEN_ENDPOINT, parameters=oauth_header_access_params_dict)

        # Create signature and add it to the headers
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer2, request_token_after_auth)
        oauth_header_access_token_params += ',oauth_signature="%s"' % signature

        access_resp = self.client.get(
            TOKEN_ENDPOINT, Authorization=oauth_header_access_token_params)
        self.assertEqual(access_resp.status_code, 200)
        content = access_resp.content.split('&')
        access_token_secret = content[0].split('=')[1]
        access_token_key = content[1].split('=')[1]
        access_token = Token.objects.get(
            secret=access_token_secret, key=access_token_key)
        #  ============= END ACCESS TOKEN =============

        if not resource_nonce:
            resource_nonce = "resource_nonce2"

        oauth_header_resource_params = "OAuth realm=\"test\", "\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"%s\","\
            "oauth_version=\"1.0\"" % (self.consumer2.key, access_token.key, str(
                int(time.time())), resource_nonce)

        self.client.logout()
        return oauth_header_resource_params, access_token

    def test_request_token_missing_headers(self):
        # Missing signature method
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token
        # function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # Create OAuth request and signature
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=INITIATE_ENDPOINT, parameters=oauth_header_request_token_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)

        # Append signature to string headers
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        resp = self.client.get(INITIATE_ENDPOINT)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content, 'Invalid request parameters.')

    def test_request_token_unsupported_headers(self):
        # Rogue oauth param added
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "this_is_not_good=\"blah\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token
        # function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # Create oauth request and signature
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=INITIATE_ENDPOINT, parameters=oauth_header_request_token_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)

        # Append signature
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        resp = self.client.get(INITIATE_ENDPOINT)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content, 'Invalid request parameters.')

    def test_request_token_duplicated_headers(self):
        # Duplicate signature_method
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token
        # function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=INITIATE_ENDPOINT, parameters=oauth_header_request_token_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)

        # Append signature
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        resp = self.client.get(INITIATE_ENDPOINT)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content, 'Invalid request parameters.')

    def test_request_token_unsupported_signature_method(self):
        # Add unsupported signature method
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"unsupported\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token
        # function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=INITIATE_ENDPOINT, parameters=oauth_header_request_token_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)

        # Append signature
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        resp = self.client.get(INITIATE_ENDPOINT)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content, 'Invalid request parameters.')

    def test_request_token_invalid_consumer_credentials(self):
        # Non existent consumer key
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"unsupported\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                "aaaaaaaaaaaaaa", str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token
        # function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=INITIATE_ENDPOINT, parameters=oauth_header_request_token_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)

        # Append signature
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        resp = self.client.get(
            INITIATE_ENDPOINT, Authorization=oauth_header_request_token_params)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.content, 'Invalid consumer.')

    def test_request_token_unknown_scope(self):
        # passing scope as form param instead of in query string in this
        # instance - scope DNE
        form_data = {
            'scope': 'DNE',
        }

        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token
        # function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=INITIATE_ENDPOINT, parameters=dict(list(oauth_header_request_token_params_dict.items()) + list(form_data.items())))
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)

        # Add signature
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(INITIATE_ENDPOINT, Authorization=oauth_header_request_token_params, data=form_data,
                                       content_type="x-www-form-urlencoded")
        self.assertEqual(request_resp.status_code, 400)
        self.assertEqual(request_resp.content,
                         'Could not verify OAuth request.')

    def test_request_token_wrong_scope(self):
        # passing scope as form param instead of in query string in this
        # instance
        form_data = {
            'scope': 'all',
        }

        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token
        # function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=INITIATE_ENDPOINT, parameters=dict(list(oauth_header_request_token_params_dict.items()) + list(form_data.items())))
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)

        # Add signature
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        # Change form scope from what oauth_request was made with
        form_data['scope'] = 'profile'

        request_resp = self.client.get(INITIATE_ENDPOINT, Authorization=oauth_header_request_token_params, data=form_data,
                                       content_type="x-www-form-urlencoded")
        self.assertEqual(request_resp.status_code, 400)
        self.assertEqual(request_resp.content,
                         'Could not verify OAuth request.')

    def test_request_token_same_nonce_and_time(self):
        # Nonce/timestamp/token combo should always be unique
        # Header params we're passing in
        now_time = str(int(time.time()))
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, now_time)

        # Make string params into dictionary for from_consumer_and_token
        # function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=INITIATE_ENDPOINT, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            INITIATE_ENDPOINT, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        # ========================================

        # Try to create another request token with the same nonce
        # Header params we're passing in
        oauth_header_request_token_params2 = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, now_time)

        # Make string params into dictionary for from_consumer_and_token
        # function
        request_token_param_list2 = oauth_header_request_token_params2.split(
            ",")
        oauth_header_request_token_params_dict2 = {}
        for p in request_token_param_list2:
            item = p.split("=")
            oauth_header_request_token_params_dict2[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict2['OAuth realm']

        # add scope to the existing params
        oauth_request2 = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                               http_url=INITIATE_ENDPOINT, parameters=oauth_header_request_token_params_dict2)

        # create signature and add it to the header params
        signature_method2 = oauth.SignatureMethod_HMAC_SHA1()
        signature2 = signature_method2.sign(
            oauth_request2, self.consumer, None)
        oauth_header_request_token_params2 = oauth_header_request_token_params2 + \
            ",oauth_signature=%s" % signature2

        request_resp2 = self.client.get(
            INITIATE_ENDPOINT, Authorization=oauth_header_request_token_params2)
        self.assertEqual(request_resp2.status_code, 400)

    def test_request_token_no_scope(self):
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=INITIATE_ENDPOINT, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        # Should still give request_token even w/o scope sent
        request_resp = self.client.get(
            INITIATE_ENDPOINT, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)

    def test_request_token_scope_in_form(self):
        # passing scope as form param instead of in query string in this
        # instance
        form_data = {
            'scope': 'all',
            'consumer_name': 'new_client'
        }

        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='POST',
                                                              http_url=INITIATE_ENDPOINT, parameters=dict(list(oauth_header_request_token_params_dict.items()) + list(form_data.items())))
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        # By default django's test client POSTs as multipart. We want form
        request_resp = self.client.post(INITIATE_ENDPOINT, Authorization=oauth_header_request_token_params, data=form_data,
                                        content_type="application/x-www-form-urlencoded")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)

    def test_request_token_scope_in_qs(self):
        # Set scope and consumer_name in param
        param = {
            'scope': 'all',
            'consumer_name': 'new_client'
        }
        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)

    def test_request_token_plaintext(self):
        param = {
            'scope': 'all',
            'consumer_name': 'new_client'
        }
        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)

    def test_request_token_rsa_sha1(self):
        rsa_key = RSA.importKey("""-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBALRiMLAh9iimur8V
A7qVvdqxevEuUkW4K+2KdMXmnQbG9Aa7k7eBjK1S+0LYmVjPKlJGNXHDGuy5Fw/d
7rjVJ0BLB+ubPK8iA/Tw3hLQgXMRRGRXXCn8ikfuQfjUS1uZSatdLB81mydBETlJ
hI6GH4twrbDJCR2Bwy/XWXgqgGRzAgMBAAECgYBYWVtleUzavkbrPjy0T5FMou8H
X9u2AC2ry8vD/l7cqedtwMPp9k7TubgNFo+NGvKsl2ynyprOZR1xjQ7WgrgVB+mm
uScOM/5HVceFuGRDhYTCObE+y1kxRloNYXnx3ei1zbeYLPCHdhxRYW7T0qcynNmw
rn05/KO2RLjgQNalsQJBANeA3Q4Nugqy4QBUCEC09SqylT2K9FrrItqL2QKc9v0Z
zO2uwllCbg0dwpVuYPYXYvikNHHg+aCWF+VXsb9rpPsCQQDWR9TT4ORdzoj+Nccn
qkMsDmzt0EfNaAOwHOmVJ2RVBspPcxt5iN4HI7HNeG6U5YsFBb+/GZbgfBT3kpNG
WPTpAkBI+gFhjfJvRw38n3g/+UeAkwMI2TJQS4n8+hid0uus3/zOjDySH3XHCUno
cn1xOJAyZODBo47E+67R4jV1/gzbAkEAklJaspRPXP877NssM5nAZMU0/O/NGCZ+
3jPgDUno6WbJn5cqm8MqWhW1xGkImgRk+fkDBquiq4gPiT898jusgQJAd5Zrr6Q8
AO/0isr/3aa6O6NLQxISLKcPDk2NOccAfS/xOtfOz4sJYM3+Bs4Io9+dZGSDCA54
Lw03eHTNQghS0A==
-----END PRIVATE KEY-----""")
        self.consumer.secret = rsa_key.exportKey()
        self.consumer.save()

        param = {
            'scope': 'all',
            'consumer_name': 'new_client'
        }

        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"RSA-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = SignatureMethod_RSA_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)

    def test_request_token_rsa_sha1_full_workflow(self):
        # Create a user
        User.objects.create_user('mike', 'mike@example.com', 'dino')
        self.client.login(username='mike', password='dino')

        # Register a consumer with rsa
        name = "test mike client"
        desc = "test mike client desc"
        rsa_key = """-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBALRiMLAh9iimur8V
A7qVvdqxevEuUkW4K+2KdMXmnQbG9Aa7k7eBjK1S+0LYmVjPKlJGNXHDGuy5Fw/d
7rjVJ0BLB+ubPK8iA/Tw3hLQgXMRRGRXXCn8ikfuQfjUS1uZSatdLB81mydBETlJ
hI6GH4twrbDJCR2Bwy/XWXgqgGRzAgMBAAECgYBYWVtleUzavkbrPjy0T5FMou8H
X9u2AC2ry8vD/l7cqedtwMPp9k7TubgNFo+NGvKsl2ynyprOZR1xjQ7WgrgVB+mm
uScOM/5HVceFuGRDhYTCObE+y1kxRloNYXnx3ei1zbeYLPCHdhxRYW7T0qcynNmw
rn05/KO2RLjgQNalsQJBANeA3Q4Nugqy4QBUCEC09SqylT2K9FrrItqL2QKc9v0Z
zO2uwllCbg0dwpVuYPYXYvikNHHg+aCWF+VXsb9rpPsCQQDWR9TT4ORdzoj+Nccn
qkMsDmzt0EfNaAOwHOmVJ2RVBspPcxt5iN4HI7HNeG6U5YsFBb+/GZbgfBT3kpNG
WPTpAkBI+gFhjfJvRw38n3g/+UeAkwMI2TJQS4n8+hid0uus3/zOjDySH3XHCUno
cn1xOJAyZODBo47E+67R4jV1/gzbAkEAklJaspRPXP877NssM5nAZMU0/O/NGCZ+
3jPgDUno6WbJn5cqm8MqWhW1xGkImgRk+fkDBquiq4gPiT898jusgQJAd5Zrr6Q8
AO/0isr/3aa6O6NLQxISLKcPDk2NOccAfS/xOtfOz4sJYM3+Bs4Io9+dZGSDCA54
Lw03eHTNQghS0A==
-----END PRIVATE KEY-----"""

        form = {"name": name, "description": desc,
                "rsa": True, "secret": rsa_key}
        my_regclient = self.client.post(reverse(regclient), form)
        self.assertEqual(my_regclient.status_code, 200)
        consumer = Consumer.objects.get(name=name)
        self.client.logout()

        param = {
            'scope': 'all',
            'consumer_name': name
        }

        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"RSA-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/token_ready\"" % (
                consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = SignatureMethod_RSA_SHA1()
        signature = signature_method.sign(oauth_request, consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        request_token = Token.objects.get(consumer=consumer)
        # ============= END INITIATE =============

        # ============= AUTHORIZE =============
        # Create authorize path, must have oauth_token param
        authorize_param = {'oauth_token': request_token.key}
        authorize_path = "%s?%s" % (
            AUTHORIZATION_ENDPOINT, urllib.parse.urlencode(authorize_param))

        # Try to hit auth path, made to login
        auth_resp = self.client.get(authorize_path)
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn(
            '/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(request_token.key, auth_resp['Location'])
        self.client.login(username='mike', password='dino')
        self.assertEqual(request_token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path)
        # Show return/display OAuth authorized view
        self.assertEqual(auth_resp.status_code, 200)

        # Get the form, set required fields
        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = request_token.key

        # Post data back to auth endpoint - should redirect to callback_url we
        # set in oauth headers with request token
        auth_post = self.client.post(AUTHORIZATION_ENDPOINT, data)
        self.assertEqual(auth_post.status_code, 302)
        # Check if oauth_verifier and oauth_token are returned
        self.assertIn(
            'http://example.com/token_ready?oauth_verifier=', auth_post['Location'])
        self.assertIn('oauth_token=', auth_post['Location'])
        # Get token again just to make sure
        request_token_after_auth = Token.objects.get(consumer=consumer)
        self.assertIn(request_token_after_auth.key, auth_post['Location'])
        self.assertEqual(request_token_after_auth.is_approved, True)
        #  ============= END AUTHORIZE =============

        # ============= ACCESS TOKEN =============
        # Set verifier in access_token params and create new oauth request
        oauth_header_access_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"RSA-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"%s\","\
            "oauth_version=\"1.0\","\
            "oauth_verifier=\"%s\"" % (consumer.key, request_token_after_auth.key, str(
                int(time.time())), "access_nonce", request_token_after_auth.verifier)

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_access_token_params.split(",")
        oauth_header_access_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_access_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_access_params_dict['OAuth realm']
        oauth_request = oauth.Request.from_token_and_callback(request_token_after_auth, http_method='GET',
                                                              http_url=TOKEN_ENDPOINT, parameters=oauth_header_access_params_dict)

        # Create signature and add it to the headers
        signature_method = SignatureMethod_RSA_SHA1()
        signature = signature_method.sign(
            oauth_request, consumer, request_token_after_auth)
        oauth_header_access_token_params += ',oauth_signature="%s"' % signature

        # Get access token
        access_resp = self.client.get(
            TOKEN_ENDPOINT, Authorization=oauth_header_access_token_params)
        self.assertEqual(access_resp.status_code, 200)
        content = access_resp.content.split('&')
        access_token_secret = content[0].split('=')[1]
        access_token_key = content[1].split('=')[1]
        access_token = Token.objects.get(secret=urllib.parse.unquote_plus(
            access_token_secret), key=access_token_key)
        #  ============= END ACCESS TOKEN =============

        # Set oauth headers user will use when hitting xapi endpoing and access
        # token
        oauth_header_resource_params = "OAuth realm=\"test\", "\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"RSA-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"%s\","\
            "oauth_version=\"1.0\"" % (consumer.key, access_token.key, str(
                int(time.time())), "resource_nonce")

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        path = TEST_SERVER + "/XAPI/statements"
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)

        # Create signature and add it to the headers
        signature_method = SignatureMethod_RSA_SHA1()
        signature = signature_method.sign(
            oauth_request, consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path, Authorization=oauth_header_resource_params,
                               X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 200)

    def test_request_token_rsa_sha1_wrong_key(self):
        rsa_key = RSA.importKey("""-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBALRiMLAh9iimur8V
A7qVvdqxevEuUkW4K+2KdMXmnQbG9Aa7k7eBjK1S+0LYmVjPKlJGNXHDGuy5Fw/d
7rjVJ0BLB+ubPK8iA/Tw3hLQgXMRRGRXXCn8ikfuQfjUS1uZSatdLB81mydBETlJ
hI6GH4twrbDJCR2Bwy/XWXgqgGRzAgMBAAECgYBYWVtleUzavkbrPjy0T5FMou8H
X9u2AC2ry8vD/l7cqedtwMPp9k7TubgNFo+NGvKsl2ynyprOZR1xjQ7WgrgVB+mm
uScOM/5HVceFuGRDhYTCObE+y1kxRloNYXnx3ei1zbeYLPCHdhxRYW7T0qcynNmw
rn05/KO2RLjgQNalsQJBANeA3Q4Nugqy4QBUCEC09SqylT2K9FrrItqL2QKc9v0Z
zO2uwllCbg0dwpVuYPYXYvikNHHg+aCWF+VXsb9rpPsCQQDWR9TT4ORdzoj+Nccn
qkMsDmzt0EfNaAOwHOmVJ2RVBspPcxt5iN4HI7HNeG6U5YsFBb+/GZbgfBT3kpNG
WPTpAkBI+gFhjfJvRw38n3g/+UeAkwMI2TJQS4n8+hid0uus3/zOjDySH3XHCUno
cn1xOJAyZODBo47E+67R4jV1/gzbAkEAklJaspRPXP877NssM5nAZMU0/O/NGCZ+
3jPgDUno6WbJn5cqm8MqWhW1xGkImgRk+fkDBquiq4gPiT898jusgQJAd5Zrr6Q8
AO/0isr/3aa6O6NLQxISLKcPDk2NOccAfS/xOtfOz4sJYM3+Bs4Io9+dZGSDCA54
Lw03eHTNQghS0A==
-----END PRIVATE KEY-----""")
        self.consumer.secret = rsa_key.exportKey()
        self.consumer.save()

        param = {
            'scope': 'all',
            'consumer_name': 'new_client'
        }

        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"RSA-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # create signature and add it to the header params
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % "badsignature"

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 400)

    def test_request_token_wrong_oauth_version(self):
        param = {
            'scope': 'all',
            'consumer_name': 'new_client'
        }
        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in - wrong oauth_version
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.1\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 400)

    def test_request_token_wrong_signature(self):
        param = {
            'scope': 'all',
            'consumer_name': 'new_client'
        }
        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.1\","\
            "oauth_callback=\"http://example.com/request_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # create signature and add it to the header params - adding wrong
        # signature
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % "wrongsignature"

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 400)
        self.assertEqual(request_resp.content,
                         'Could not verify OAuth request.')

    def test_auth_correct(self):
        param = {
            'scope': 'all',
            'consumer_name': 'new_client'
        }
        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/access_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)
        # ===================================================

        # Test AUTHORIZE
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (
            AUTHORIZATION_ENDPOINT, urllib.parse.urlencode(param))

        auth_resp = self.client.get(authorize_path)
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn(
            '/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path)
        # Show return/display OAuth authorized view
        self.assertEqual(auth_resp.status_code, 200)

        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = token.key

        auth_post = self.client.post(AUTHORIZATION_ENDPOINT, data)
        self.assertEqual(auth_post.status_code, 302)
        # Check if oauth_verifier and oauth_token are returned
        self.assertIn(
            'http://example.com/access_token_ready?oauth_verifier=', auth_post['Location'])
        self.assertIn('oauth_token=', auth_post['Location'])
        access_token = Token.objects.get(consumer=self.consumer)
        self.assertIn(access_token.key, auth_post['Location'])
        self.assertEqual(access_token.is_approved, True)

    def test_auth_scope_up(self):
        param = {
            'scope': 'statements/read',
            'consumer_name': 'new_client'
        }
        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/access_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)
        # =================================================

        # Test AUTHORIZE
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (
            AUTHORIZATION_ENDPOINT, urllib.parse.urlencode(param))

        auth_resp = self.client.get(authorize_path)
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn(
            '/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path)
        # Show return/display OAuth authorized view
        self.assertEqual(auth_resp.status_code, 200)

        # Increase power of scope here - not allowed
        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = token.key
        data['scopes'] = ['all']

        auth_post = self.client.post(AUTHORIZATION_ENDPOINT, data)
        self.assertEqual(auth_post.status_code, 401)
        self.assertEqual(auth_post.content, 'Action not allowed.')

    def test_auth_wrong_auth(self):
        param = {
            'scope': 'statements/read',
            'consumer_name': 'new_client'
        }
        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/access_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)
        # =================================================

        # Test AUTHORIZE
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (
            AUTHORIZATION_ENDPOINT, urllib.parse.urlencode(param))

        auth_resp = self.client.get(authorize_path)
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn(
            '/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])
        # Login with wrong user the client is associated with
        self.client.login(username='dick', password='lassie')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path)
        # Show return/display OAuth authorized view
        self.assertEqual(auth_resp.status_code, 403)
        self.assertEqual(auth_resp.content, 'Invalid user for this client.')

    def test_auth_no_scope_chosen(self):
        param = {
            'scope': 'statements/read',
            'consumer_name': 'new_client'
        }
        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/access_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)
        # =================================================

        # Test AUTHORIZE
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (
            AUTHORIZATION_ENDPOINT, urllib.parse.urlencode(param))

        auth_resp = self.client.get(authorize_path)
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn(
            '/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path)
        # Show return/display OAuth authorized view
        self.assertEqual(auth_resp.status_code, 200)

        # User must select at least one scope
        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = token.key
        data['scopes'] = []

        auth_post = self.client.post(AUTHORIZATION_ENDPOINT, data)
        self.assertEqual(auth_post.status_code, 401)
        self.assertEqual(auth_post.content, 'Action not allowed.')

    def test_access_token_invalid_token(self):
        param = {
            'scope': 'all',
            'consumer_name': 'new_client'
        }
        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"requestnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/access_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)
        # ==================================================

        # Test AUTHORIZE
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (
            AUTHORIZATION_ENDPOINT, urllib.parse.urlencode(param))

        auth_resp = self.client.get(authorize_path)
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn(
            '/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path)
        # Show return/display OAuth authorized view
        self.assertEqual(auth_resp.status_code, 200)

        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = token.key

        auth_post = self.client.post(AUTHORIZATION_ENDPOINT, data)
        self.assertEqual(auth_post.status_code, 302)
        # Check if oauth_verifier and oauth_token are returned
        self.assertIn(
            'http://example.com/access_token_ready?oauth_verifier=', auth_post['Location'])
        self.assertIn('oauth_token=', auth_post['Location'])
        access_token = Token.objects.get(consumer=self.consumer)
        self.assertIn(access_token.key, auth_post['Location'])
        self.assertEqual(access_token.is_approved, True)
        # Set is approved false for the token
        access_token.is_approved = False
        access_token.save()

        # Test ACCESS TOKEN
        oauth_header_access_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_signature=\"%s&%s\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"accessnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_verifier=\"%s\"" % (self.consumer.key, token.key, self.consumer.secret, token.secret, str(
                int(time.time())), token.verifier)

        access_resp = self.client.get(
            TOKEN_ENDPOINT, Authorization=oauth_header_access_params)
        self.assertEqual(access_resp.status_code, 401)
        self.assertEqual(access_resp.content,
                         "Request Token not approved by the user.")

    def test_access_token_access_resources(self):
        param = {
            'scope': 'all',
            'consumer_name': 'new_client'
        }
        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"12345678\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/access_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=oauth_header_request_token_params)
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)
        # =========================================================

        # Test AUTHORIZE
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (
            AUTHORIZATION_ENDPOINT, urllib.parse.urlencode(param))

        auth_resp = self.client.get(authorize_path)
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn(
            '/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path)
        # Show return/display OAuth authorized view
        self.assertEqual(auth_resp.status_code, 200)

        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = token.key

        auth_post = self.client.post(AUTHORIZATION_ENDPOINT, data)
        self.assertEqual(auth_post.status_code, 302)
        # Check if oauth_verifier and oauth_token are returned
        self.assertIn(
            'http://example.com/access_token_ready?oauth_verifier=', auth_post['Location'])
        self.assertIn('oauth_token=', auth_post['Location'])
        request_token = Token.objects.get(consumer=self.consumer)
        self.assertIn(request_token.key, auth_post['Location'])
        self.assertEqual(request_token.is_approved, True)
        # ===========================================================

        # Test ACCESS TOKEN
        oauth_header_access_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_signature=\"%s&%s\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"87654321\","\
            "oauth_version=\"1.0\","\
            "oauth_verifier=\"%s\"" % (self.consumer.key, token.key, self.consumer.secret, request_token.secret, str(
                int(time.time())), request_token.verifier)

        access_resp = self.client.get(
            TOKEN_ENDPOINT, Authorization=oauth_header_access_params)
        self.assertEqual(access_resp.status_code, 200)
        content = access_resp.content.split('&')
        access_token_secret = content[0].split('=')[1]
        access_token_key = content[1].split('=')[1]
        access_token = Token.objects.get(
            secret=access_token_secret, key=access_token_key)
        # ==============================================================

        # Test ACCESS RESOURCE
        oauth_header_resource_params = "OAuth realm=\"test\", "\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"accessresourcenonce\","\
            "oauth_version=\"1.0\"" % (
                self.consumer.key, access_token.key, str(int(time.time())))

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        path = TEST_SERVER + "/XAPI/statements"
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)

        # Create signature and add it to the headers
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path, Authorization=oauth_header_resource_params,
                               X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 200)

    def test_unicode(self):
        # All client requests have the auth as unicode
        # ============= INITIATE =============
        param = {
            'scope': 'all',
            'consumer_name': 'new_client'
        }
        request_token_path = "%s?%s" % (
            INITIATE_ENDPOINT, urllib.parse.urlencode(param))
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"12345678\","\
            "oauth_version=\"1.0\","\
            "oauth_callback=\"http://example.com/access_token_ready\"" % (
                self.consumer.key, str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # get_oauth_request in views ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
                                                              http_url=request_token_path, parameters=oauth_header_request_token_params_dict)

        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + \
            ",oauth_signature=%s" % signature

        request_resp = self.client.get(
            request_token_path, Authorization=str(oauth_header_request_token_params))
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)
        # ============= END INITIATE =============

        # ============= AUTHORIZE =============
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (
            AUTHORIZATION_ENDPOINT, urllib.parse.urlencode(param))

        auth_resp = self.client.get(authorize_path)
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn(
            '/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path)
        # Show return/display OAuth authorized view
        self.assertEqual(auth_resp.status_code, 200)

        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = token.key

        auth_post = self.client.post(AUTHORIZATION_ENDPOINT, data)
        self.assertEqual(auth_post.status_code, 302)
        # Check if oauth_verifier and oauth_token are returned
        self.assertIn(
            'http://example.com/access_token_ready?oauth_verifier=', auth_post['Location'])
        self.assertIn('oauth_token=', auth_post['Location'])
        request_token = Token.objects.get(consumer=self.consumer)
        self.assertIn(request_token.key, auth_post['Location'])
        self.assertEqual(request_token.is_approved, True)
        #  ============= END AUTHORIZE =============

        # ============= ACCESS TOKEN =============
        oauth_header_access_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"87654321\","\
            "oauth_version=\"1.0\","\
            "oauth_verifier=\"%s\"" % (self.consumer.key, token.key, str(
                int(time.time())), request_token.verifier)

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_access_params.split(",")
        oauth_header_access_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_access_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_access_params_dict['OAuth realm']
        oauth_request = oauth.Request.from_token_and_callback(request_token, http_method='GET',
                                                              http_url=TOKEN_ENDPOINT, parameters=oauth_header_access_params_dict)

        # Create signature and add it to the headers
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, request_token)
        oauth_header_access_params += ',oauth_signature="%s"' % signature

        access_resp = self.client.get(
            TOKEN_ENDPOINT, Authorization=str(oauth_header_access_params))
        self.assertEqual(access_resp.status_code, 200)
        content = access_resp.content.split('&')
        access_token_secret = content[0].split('=')[1]
        access_token_key = content[1].split('=')[1]
        access_token = Token.objects.get(
            secret=access_token_secret, key=access_token_key)
        #  ============= END ACCESS TOKEN =============

        # ============= ACCESS RESOURCE =============
        oauth_header_resource_params = "OAuth realm=\"test\", "\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"accessresourcenonce\","\
            "oauth_version=\"1.0\"" % (
                self.consumer.key, access_token.key, str(int(time.time())))

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        path = TEST_SERVER + "/XAPI/statements"
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)

        # Create signature and add it to the headers
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path, Authorization=str(
            oauth_header_resource_params), X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 200)

    def test_oauth_disabled(self):
        # Disable oauth
        if settings.OAUTH_ENABLED:
            settings.OAUTH_ENABLED = False

        put_guid = str(uuid.uuid1())
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bill"},
                           "verb": {"id": "http://example.com/verbs/accessed", "display": {"en-US": "accessed"}},
                           "object": {"id": "act:test_put"}})
        param = {"statementId": put_guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements',
                          urllib.parse.urlencode(param))

        oauth_header_resource_params, access_token = self.oauth_handshake()

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='PUT',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)

        # build signature and add to the params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        # Put statements
        resp = self.client.put(path, data=stmt, content_type="application/json",
                               Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.content, "OAuth is not enabled. To enable, set the OAUTH_ENABLED flag to true in settings")

    def test_stmt_put(self):
        # build stmt data and path
        put_guid = str(uuid.uuid1())
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bill"},
                           "verb": {"id": "http://example.com/verbs/accessed", "display": {"en-US": "accessed"}},
                           "object": {"id": "act:test_put"}})
        param = {"statementId": put_guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements',
                          urllib.parse.urlencode(param))

        # Get oauth header params and access token
        oauth_header_resource_params, access_token = self.oauth_handshake()

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request to PUT the stmt
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='PUT',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)

        # build signature and add to the params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        # Put statements
        resp = self.client.put(path, data=stmt, content_type="application/json",
                               Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 204)

    def test_stmt_post_no_scope(self):
        stmt = {"actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob"},
                "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                "object": {"id": "act:test_post"}}
        stmt_json = json.dumps(stmt)

        # Don't send scope so it defaults to statements/write and
        # statements/read/mine
        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope=False)

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth_request and apply signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='POST',
                                                              http_url='http://testserver/XAPI/statements', parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        post = self.client.post(reverse('lrs:statements'), data=stmt_json, content_type="application/json",
                                Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 200)

    def test_stmt_simple_get(self):
        guid = str(uuid.uuid1())
        stmt_data = {"id": guid, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob"},
                     "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                     "object": {"id": "act:test_simple_get"}, "authority": {"objectType": "Agent", "mbox": "mailto:jane@example.com"}}
        stmt_post = self.client.post(reverse('lrs:statements'), json.dumps(stmt_data), content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        param = {"statementId": guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements',
                          urllib.parse.urlencode(param))
        oauth_header_resource_params, access_token = self.oauth_handshake()

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and apply signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path, Authorization=oauth_header_resource_params,
                               X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 200)
        rsp = resp.content
        self.assertIn(guid, rsp)

    def test_stmt_complex_get(self):
        stmt_data = {"actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob"},
                     "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                     "object": {"id": "act:test_complex_get"}, "authority": {"objectType": "Agent", "mbox": "mailto:jane@example.com"}}
        stmt_post = self.client.post(reverse('lrs:statements'), json.dumps(stmt_data), content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        param = {"activity": "act:test_complex_get"}
        path = "%s?%s" % ('http://testserver/XAPI/statements',
                          urllib.parse.urlencode(param))

        oauth_header_resource_params, access_token = self.oauth_handshake()

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and apply signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path, Authorization=oauth_header_resource_params,
                               X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 200)

    def test_stmt_get_then_wrong_scope(self):
        guid = str(uuid.uuid1())
        stmt_data = {"id": guid, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob"},
                     "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                     "object": {"id": "act:test_simple_get"}, "authority": {"objectType": "Agent", "mbox": "mailto:jane@example.com"}}
        stmt_post = self.client.post(reverse('lrs:statements'), json.dumps(stmt_data), content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        param = {"statementId": guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements',
                          urllib.parse.urlencode(param))

        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type="statements/read profile")

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature to get statements
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path, Authorization=oauth_header_resource_params,
                               X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 200)
        rsp = resp.content
        self.assertIn(guid, rsp)
        # =============================================

        # Test POST (not allowed)
        post_stmt = {"actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob"},
                     "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                     "object": {"id": "act:test_post"}}
        post_stmt_json = json.dumps(post_stmt)

        # Use same oauth headers, change the nonce
        oauth_header_resource_params_dict['oauth_nonce'] = 'another_nonce'

        # create another oauth request
        oauth_request2 = oauth.Request.from_token_and_callback(access_token, http_method='POST',
                                                               http_url='http://testserver/XAPI/statements', parameters=oauth_header_resource_params_dict)
        signature_method2 = oauth.SignatureMethod_HMAC_SHA1()
        signature2 = signature_method2.sign(
            oauth_request2, self.consumer, access_token)

        # Replace old signature and add the new one
        oauth_header_resource_params = oauth_header_resource_params.replace(
            '"%s"' % signature, '"%s"' % signature2)
        # replace headers with the nonce you added in dict
        oauth_header_resource_params = oauth_header_resource_params.replace(
            'oauth_nonce="resource_nonce"', 'oauth_nonce="another_nonce"')

        post = self.client.post(reverse('lrs:statements'), data=post_stmt_json, content_type="application/json",
                                Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 403)
        self.assertEqual(
            post.content, 'Incorrect permissions to POST at /xapi/statements')

    def test_activity_state_put_then_wrong_scope(self):
        url = TEST_SERVER + '/XAPI/activities/state'
        testagent = '{"name":"jane","mbox":"mailto:jane@example.com"}'
        activityId = "http://www.iana.org/domains/example/"
        stateId = "id:the_state_id"
        activity = Activity(activity_id=activityId)
        activity.save()
        testparams = {"stateId": stateId,
                      "activityId": activityId, "agent": testagent}
        teststate = {"test": "put activity state 1"}
        path = '%s?%s' % (url, urllib.parse.urlencode(testparams))

        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type='state')

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='PUT',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        put = self.client.put(path, data=teststate, content_type="application/json",
                              Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put.status_code, 204)
        # ==========================================================

        # Set up for Get
        guid = str(uuid.uuid1())
        stmt_data = {"id": guid, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob"},
                     "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                     "object": {"id": "act:test_simple_get"}, "authority": {"objectType": "Agent", "mbox": "mailto:jane@example.com"}}
        stmt_post = self.client.post(reverse('lrs:statements'), json.dumps(stmt_data), content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        param = {"statementId": guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements',
                          urllib.parse.urlencode(param))

        # Use same oauth_headers as before and change the nonce
        oauth_header_resource_params_dict['oauth_nonce'] = 'differ_nonce'

        # create another oauth request
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature2 = signature_method.sign(
            oauth_request, self.consumer, access_token)
        # Replace old signature with the new one
        oauth_header_resource_params_new = oauth_header_resource_params.replace(
            '"%s"' % signature, '"%s"' % signature2)
        # replace headers with the nonce you added in dict
        new_oauth_headers = oauth_header_resource_params_new.replace(
            'oauth_nonce="resource_nonce"', 'oauth_nonce="differ_nonce"')

        get = self.client.get(path, content_type="application/json",
                              Authorization=new_oauth_headers, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(get.status_code, 403)
        self.assertEqual(
            get.content, 'Incorrect permissions to GET at /xapi/statements')

    def stmt_get_then_wrong_profile_scope(self):
        guid = str(uuid.uuid1())
        stmt_data = {"id": guid, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob"},
                     "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                     "object": {"id": "act:test_simple_get"}, "authority": {"objectType": "Agent", "mbox": "mailto:jane@example.com"}}
        stmt_post = self.client.post(reverse('lrs:statements'), json.dumps(stmt_data), content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        param = {"statementId": guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements',
                          urllib.parse.urlencode(param))

        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type="statements/read")

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path, Authorization=oauth_header_resource_params,
                               X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 200)
        rsp = resp.content
        self.assertIn(guid, rsp)
        # ===================================================================

        url = 'http://testserver/XAPI/agents/profile'
        params = {"agent": {"mbox": "mailto:test@example.com"}}
        path = "%s?%s" % (url, urllib.parse.urlencode(params))

        # Use same oauth header, change nonce
        oauth_header_resource_params_dict['oauth_nonce'] = 'differ_nonce'

        # create another oauth request
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method2 = oauth.SignatureMethod_HMAC_SHA1()
        signature2 = signature_method2.sign(
            oauth_request, self.consumer, access_token)
        # Replace signature with new one
        new_sig_params = oauth_header_resource_params.replace(
            '"%s"' % signature, '"%s"' % signature2)
        # replace headers with the nonce you added in dict
        new_oauth_headers = new_sig_params.replace(
            'oauth_nonce="resource_nonce"', 'oauth_nonce="differ_nonce"')

        r = self.client.get(path, Authorization=new_oauth_headers,
                            X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 403)

    def test_consumer_state(self):
        stmt_data = {"actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob"},
                     "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                     "object": {"id": "act:test_complex_get"}, "authority": {"objectType": "Agent", "mbox": "mailto:jane@example.com"}}
        stmt_post = self.client.post(reverse('lrs:statements'), json.dumps(stmt_data), content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        param = {"object": {"objectType": "Activity",
                            "id": "act:test_complex_get"}}
        path = "%s?%s" % ('http://testserver/XAPI/statements',
                          urllib.parse.urlencode(param))

        oauth_header_resource_params, access_token = self.oauth_handshake()

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        # Change the consumer state
        consumer = access_token.consumer
        consumer.status = 4
        consumer.save()

        resp = self.client.get(path, Authorization=oauth_header_resource_params,
                               X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.content, 'Invalid Consumer.')

    def test_simple_stmt_get_mine_only(self):
        guid = str(uuid.uuid1())
        # Put statement normally
        username = "tester1"
        email = "test1@tester.com"
        password = "test"
        auth = "Basic %s" % base64.b64encode("%s:%s" % (username, password))
        form = {"username": username, "email": email,
                "password": password, "password2": password}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.logout()

        param = {"statementId": guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})

        put_resp = self.client.put(path, stmt, content_type="application/json",
                                   Authorization=auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_resp.status_code, 204)

        param = {"statementId": guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements',
                          urllib.parse.urlencode(param))
        # ====================================================

        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type="statements/read/mine")

        # From_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path, Authorization=oauth_header_resource_params,
                               X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 403)
        # ===================================================

        # build stmt data and path
        oauth_agent1 = Agent.objects.get(account_name=self.consumer.key)
        oauth_agent2 = Agent.objects.get(mbox="mailto:test1@tester.com")
        oauth_group = Agent.objects.get(
            member__in=[oauth_agent1, oauth_agent2])
        guid = str(uuid.uuid1())

        stmt_data = {"id": guid, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bill"},
                     "verb": {"id": "http://example.com/verbs/accessed", "display": {"en-US": "accessed"}},
                     "object": {"id": "act:test_put"}, "authority": oauth_group.to_dict()}

        settings.ALLOW_EMPTY_HTTP_AUTH = True

        stmt_post = self.client.post(reverse('lrs:statements'), json.dumps(stmt_data), content_type="application/json",
                                     Authorization="Basic %s" % base64.b64encode("%s:%s" % ('', '')), X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        param = {"statementId": guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements',
                          urllib.parse.urlencode(param))

        # Use same oauth headers but replace the nonce
        oauth_header_resource_params_dict['oauth_nonce'] = 'get_differ_nonce'

        # Create another oauth request, replace the signature with new one and
        # change the nonce
        oauth_request2 = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                               http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method2 = oauth.SignatureMethod_HMAC_SHA1()
        signature2 = signature_method2.sign(
            oauth_request2, self.consumer, access_token)
        sig = oauth_header_resource_params.replace(
            '"%s"' % signature, '"%s"' % signature2)
        new_oauth_headers = sig.replace(
            'oauth_nonce="resource_nonce"', 'oauth_nonce="get_differ_nonce"')

        get = self.client.get(path, content_type="application/json",
                              Authorization=new_oauth_headers, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(get.status_code, 200)
        settings.ALLOW_EMPTY_HTTP_AUTH = False

    def test_complex_stmt_get_mine_only(self):
        guid = str(uuid.uuid1())
        username = "tester1"
        email = "test1@tester.com"
        password = "test"
        auth = "Basic %s" % base64.b64encode("%s:%s" % (username, password))
        form = {"username": username, "email": email,
                "password": password, "password2": password}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.logout()

        # Put statement
        param = {"statementId": guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})

        put_response = self.client.put(path, stmt, content_type="application/json",
                                       Authorization=auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_response.status_code, 204)
        # =============================================

        param = {"statementId": guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements',
                          urllib.parse.urlencode(param))

        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type="statements/read/mine")

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path, Authorization=oauth_header_resource_params,
                               X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 403)
        # ====================================================

        # Should return 0 statements since the only statement is not this user's
        # Use same oauth headers but replace the nonce
        oauth_header_resource_params_dict['oauth_nonce'] = 'differ_nonce'

        # Create another oauth request and add the signature
        oauth_request2 = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                               http_url='http://testserver/XAPI/statements', parameters=oauth_header_resource_params_dict)
        signature_method2 = oauth.SignatureMethod_HMAC_SHA1()
        signature2 = signature_method2.sign(
            oauth_request2, self.consumer, access_token)
        sig = oauth_header_resource_params.replace(
            '"%s"' % signature, '"%s"' % signature2)
        new_oauth_headers = sig.replace(
            'oauth_nonce="resource_nonce"', 'oauth_nonce="differ_nonce"')

        # Get statements
        get = self.client.get('http://testserver/XAPI/statements', content_type="application/json",
                              Authorization=new_oauth_headers, X_Experience_API_Version=settings.XAPI_VERSION)
        get_content = json.loads(get.content)
        self.assertEqual(get.status_code, 200)
        self.assertEqual(len(get_content['statements']), 0)
        # ====================================================

        # Should return the newly created single statement
        # build stmt data and path
        oauth_agent1 = Agent.objects.get(account_name=self.consumer.key)
        oauth_agent2 = Agent.objects.get(mbox="mailto:test1@tester.com")
        oauth_group = Agent.objects.get(
            member__in=[oauth_agent1, oauth_agent2])
        guid = str(uuid.uuid1())

        stmt_data = {"id": guid, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bill"},
                     "verb": {"id": "http://example.com/verbs/accessed", "display": {"en-US": "accessed"}},
                     "object": {"id": "act:test_put"}, "authority": oauth_group.to_dict()}
        stmt_post = self.client.post(reverse('lrs:statements'), json.dumps(stmt_data), content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        # Use same headers, change nonce
        oauth_header_resource_params_dict['oauth_nonce'] = 'get_differ_nonce'

        # Create oauth request and add signature
        oauth_request3 = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                               http_url='http://testserver/XAPI/statements', parameters=oauth_header_resource_params_dict)
        signature_method3 = oauth.SignatureMethod_HMAC_SHA1()
        signature3 = signature_method3.sign(
            oauth_request3, self.consumer, access_token)

        sig2 = oauth_header_resource_params.replace(
            '"%s"' % signature, '"%s"' % signature3)
        new_oauth_headers2 = sig2.replace(
            'oauth_nonce="resource_nonce"', 'oauth_nonce="get_differ_nonce"')

        # Get statements
        get2 = self.client.get('http://testserver/XAPI/statements', content_type="application/json",
                               Authorization=new_oauth_headers2, X_Experience_API_Version=settings.XAPI_VERSION)
        get_content2 = json.loads(get2.content)
        self.assertEqual(get2.status_code, 200)

        self.assertEqual(get_content2['statements'][
                         0]['actor']['name'], 'bill')
        self.assertEqual(len(get_content2['statements']), 1)

    def test_state_wrong_auth(self):
        # This test agent is not in this auth
        url = 'http://testserver/XAPI/activities/state'
        testagent = '{"name":"dick","mbox":"mailto:dick@example.com"}'
        activityId = "http://www.iana.org/domains/example/"
        stateId = "id:the_state_id"
        activity = Activity(activity_id=activityId)
        activity.save()
        testparams = {"stateId": stateId,
                      "activityId": activityId, "agent": testagent}
        teststate = {"test": "put activity state 1"}
        path = '%s?%s' % (url, urllib.parse.urlencode(testparams))

        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type='state')

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='PUT',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        put = self.client.put(path, data=teststate, content_type="application/json",
                              Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put.status_code, 403)
        self.assertEqual(
            put.content, "Agent for state is out of scope")

    def test_profile_wrong_auth(self):
        agent = Agent(name="joe", mbox="mailto:joe@example.com")
        agent.save()

        # Agent is not in this auth
        url = 'http://testserver/XAPI/agents/profile'
        testparams = {
            "agent": '{"name":"joe","mbox":"mailto:joe@example.com"}'}
        path = '%s?%s' % (url, urllib.parse.urlencode(testparams))

        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type='profile')

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        get = self.client.get(path, content_type="application/json",
                              Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(get.status_code, 403)
        self.assertEqual(
            get.content, "Agent for agent profile is out of scope")

    def test_define_scope_activity(self):
        url = 'http://testserver/XAPI/statements'
        guid = str(uuid.uuid1())
        stmt_data = {"id": guid, "actor": {"objectType": "Agent",
                                           "mbox": "mailto:bob@bob.com", "name": "bob"}, "verb": {"id": "http://example.com/verbs/passed",
                                                                                                  "display": {"en-US": "passed"}}, "object": {"id": "test://test/define/scope"},
                     "authority": {"objectType": "Agent", "mbox": "mailto:jane@example.com"}}
        stmt_post = self.client.post(reverse('lrs:statements'), json.dumps(stmt_data), content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        # build stmt data and path
        put_guid = str(uuid.uuid1())
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:bill@bill.com", "name": "bill"},
                           "verb": {"id": "http://example.com/verbs/accessed", "display": {"en-US": "accessed"}},
                           "object": {"id": "test://test/define/scope",
                                      'definition': {'name': {'en-US': 'testname', 'en-GB': 'altname'},
                                                     'description': {'en-US': 'testdesc', 'en-GB': 'altdesc'}, 'type': 'type:course',
                                                     'interactionType': 'other', 'correctResponsesPattern': []}}})

        param = {"statementId": put_guid}
        path = "%s?%s" % (url, urllib.parse.urlencode(param))

        # START PUT STMT
        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type='statements/write statements/read')

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='PUT',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        # Put statements - does not have define scope, therefore it cannot
        # update the activity
        resp = self.client.put(path, data=stmt, content_type="application/json",
                               Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(resp.status_code, 204)
        acts = Activity.objects.all()
        self.assertEqual(len(acts), 1)
        # ==========================================================

        # START GET STMT
        get_params = {"activity": "test://test/define/scope"}
        path = "%s?%s" % (url, urllib.parse.urlencode(get_params))

        # User same oauth headers, change nonce
        oauth_header_resource_params_dict['oauth_nonce'] = 'get_differ_nonce'

        # Create oauth request and add signature
        oauth_request2 = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                               http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method2 = oauth.SignatureMethod_HMAC_SHA1()
        signature2 = signature_method2.sign(
            oauth_request2, self.consumer, access_token)
        sig = oauth_header_resource_params.replace(
            '"%s"' % signature, '"%s"' % signature2)
        new_oauth_headers = sig.replace(
            'oauth_nonce="resource_nonce"', 'oauth_nonce="get_differ_nonce"')

        get_resp = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=new_oauth_headers)
        self.assertEqual(get_resp.status_code, 200)
        content = json.loads(get_resp.content)
        self.assertEqual(len(content['statements']), 2)
        self.client.logout()
        # ==========================================================

        # START OF POST WITH ANOTHER HANDSHAKE
        post_stmt = {"actor": {"objectType": "Agent", "mbox": "mailto:dom@dom.com", "name": "dom"},
                     "verb": {"id": "http://example.com/verbs/tested", "display": {"en-US": "tested"}},
                     "object": {"id": "test://test/define/scope",
                                'definition': {'name': {'en-US': 'definename', 'en-GB': 'definealtname'},
                                               'description': {'en-US': 'definedesc', 'en-GB': 'definealtdesc'}, 'type': 'type:course',
                                               'interactionType': 'other', 'correctResponsesPattern': []}}}
        stmt_json = json.dumps(post_stmt)

        post_oauth_header_resource_params, post_access_token = self.oauth_handshake2(
            scope_type='define statements/write')

        # from_token_and_callback takes a dictionary
        post_param_list = post_oauth_header_resource_params.split(",")
        post_oauth_header_resource_params_dict = {}
        for p in post_param_list:
            item = p.split("=")
            post_oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del post_oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        post_oauth_request = oauth.Request.from_token_and_callback(post_access_token, http_method='POST',
                                                                   http_url='http://testserver/XAPI/statements',
                                                                   parameters=post_oauth_header_resource_params_dict)
        post_signature_method = oauth.SignatureMethod_HMAC_SHA1()
        post_signature = post_signature_method.sign(
            post_oauth_request, self.consumer2, post_access_token)
        post_oauth_header_resource_params += ',oauth_signature="%s"' % post_signature

        # Even though dick has define scope, he didn't create the activity so
        # he can't update it
        post = self.client.post(reverse('lrs:statements'), data=stmt_json, content_type="application/json",
                                Authorization=post_oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 200)
        acts = Activity.objects.all()
        self.assertEqual(len(acts), 1)
        self.assertNotIn("definition", list(acts[
                         0].return_activity_with_lang_format().keys()))

    def test_define_scope_agent(self):
        url = 'http://testserver/XAPI/statements'
        guid = str(uuid.uuid1())
        stmt_data = {"id": guid, "actor": {"objectType": "Agent",
                                           "mbox": "mailto:bob@bob.com", "name": "bob"}, "verb": {"id": "http://example.com/verbs/helped",
                                                                                                  "display": {"en-US": "helped"}}, "object": {"objectType": "Agent", "mbox": "mailto:tim@tim.com",
                                                                                                                                              "name": "tim"}}
        stmt_post = self.client.post(reverse('lrs:statements'), json.dumps(stmt_data), content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        # build stmt data and path
        put_guid = str(uuid.uuid1())
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:bill@bill.com", "name": "bill"},
                           "verb": {"id": "http://example.com/verbs/talked", "display": {"en-US": "talked"}},
                           "object": {"objectType": "Agent", "mbox": "mailto:tim@tim.com", "name": "tim timson"}})

        param = {"statementId": put_guid}
        path = "%s?%s" % (url, urllib.parse.urlencode(param))

        # START PUT STMT
        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type='statements/write statements/read')

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='PUT',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        # Put statements
        resp = self.client.put(path, data=stmt, content_type="application/json",
                               Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 204)
        agents = Agent.objects.all().values_list('name', flat=True)
        # Jane, Bill, Tim, Bob, Dick, Anonymous Group and Account
        self.assertEqual(len(agents), 7)
        self.assertIn('tim', agents)
        self.assertNotIn('tim timson', agents)
        # =================================================

        # START GET STMT
        get_params = {"agent": {"objectType": "Agent",
                                "mbox": "mailto:tim@tim.com"}, "related_agents": True}
        path = "%s?%s" % (url, urllib.parse.urlencode(get_params))

        # Use same oauth headers, replace nonce
        oauth_header_resource_params_dict['oauth_nonce'] = 'get_differ_nonce'

        # Create oauth request and add signature
        oauth_request2 = oauth.Request.from_token_and_callback(access_token, http_method='GET',
                                                               http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method2 = oauth.SignatureMethod_HMAC_SHA1()
        signature2 = signature_method2.sign(
            oauth_request2, self.consumer, access_token)
        sig = oauth_header_resource_params.replace(
            '"%s"' % signature, '"%s"' % signature2)
        new_oauth_headers = sig.replace(
            'oauth_nonce="resource_nonce"', 'oauth_nonce="get_differ_nonce"')

        get_resp = self.client.get(path, X_Experience_API_Version=settings.XAPI_VERSION,
                                   Authorization=new_oauth_headers)
        self.assertEqual(get_resp.status_code, 200)
        content = json.loads(get_resp.content)
        # Should be two since querying by tim email.
        self.assertEqual(len(content['statements']), 2)
        self.client.logout()
        # ==================================================

        # START OF POST WITH ANOTHER HANDSHAKE
        # Anonymous group that will make 2 canonical agents
        ot = "Group"
        members = [{"name": "john doe", "mbox": "mailto:jd@example.com"},
                   {"name": "jan doe", "mbox": "mailto:jandoe@example.com"}]
        kwargs = {"objectType": ot, "member": members, "name": "doe group"}
        global_group, created = Agent.objects.retrieve_or_create(**kwargs)

        # Anonymous group that will retrieve two agents and create one more
        # canonical agents
        members = [{"name": "john doe", "mbox": "mailto:jd@example.com"},
                   {"name": "jan doe", "mbox": "mailto:jandoe@example.com"},
                   {"name": "dave doe", "mbox": "mailto:dd@example.com"}]
        kwargs1 = {"objectType": ot, "member": members, "name": "doe group"}

        post_stmt = {"actor": {"objectType": "Agent", "mbox": "mailto:dom@dom.com", "name": "dom"},
                     "verb": {"id": "http://example.com/verbs/assisted", "display": {"en-US": "assisted"}},
                     "object": kwargs1}
        stmt_json = json.dumps(post_stmt)

        post_oauth_header_resource_params, post_access_token = self.oauth_handshake2(
            scope_type='statements/write statements/read')

        # from_token_and_callback takes a dictionary
        post_param_list = post_oauth_header_resource_params.split(",")
        post_oauth_header_resource_params_dict = {}
        for p in post_param_list:
            item = p.split("=")
            post_oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del post_oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        post_oauth_request = oauth.Request.from_token_and_callback(post_access_token, http_method='POST',
                                                                   http_url='http://testserver/XAPI/statements',
                                                                   parameters=post_oauth_header_resource_params_dict)
        post_signature_method = oauth.SignatureMethod_HMAC_SHA1()
        post_signature = post_signature_method.sign(post_oauth_request, self.consumer2,
                                                    post_access_token)
        post_oauth_header_resource_params += ',oauth_signature="%s"' % post_signature

        post = self.client.post(reverse('lrs:statements'), data=stmt_json, content_type="application/json",
                                Authorization=post_oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 200)
        agents = Agent.objects.all().values_list('name', flat=True)
        # 2 oauth group objects and 2 anon account agents for oauth, all of these agents since created with member or manually, 2 agents for
        # jand and dick users, 2 doe groups since can't update anymore
        self.assertEqual(len(agents), 15)
        self.assertIn('bill', agents)
        self.assertNotIn('tim timson', agents)
        self.assertIn('dom', agents)
        self.assertIn('bob', agents)
        self.assertIn('tim', agents)
        self.assertIn('jan doe', agents)
        self.assertIn('john doe', agents)
        self.assertIn('dave doe', agents)
        self.assertIn('jane', agents)
        self.assertIn('dick', agents)
        self.assertIn('doe group', agents)

    def test_default_scope_multiple_requests(self):
        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope=False)

        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_post"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})

        # from_token_and_callback takes a dictionary
        post_param_list = oauth_header_resource_params.split(",")
        post_oauth_header_resource_params_dict = {}
        for p in post_param_list:
            item = p.split("=")
            post_oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')

        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del post_oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        post_oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='POST',
                                                                   http_url=TEST_SERVER + '/XAPI/statements', parameters=post_oauth_header_resource_params_dict)
        post_signature_method = oauth.SignatureMethod_HMAC_SHA1()
        post_signature = post_signature_method.sign(
            post_oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % post_signature

        post = self.client.post(TEST_SERVER + '/XAPI/statements', data=stmt, content_type="application/json",
                                Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 200)
        # ====================================================
        stmt2 = json.dumps({"verb": {"id": "http://example.com/verbs/failed", "display": {"en-US": "failed"}},
                            "object": {"id": "act:test_post"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})

        # Use same oauth headers, replace nonce
        post_oauth_header_resource_params_dict[
            'oauth_nonce'] = 'post_differ_nonce'

        # Create oauth request and add signature
        post_oauth_request2 = oauth.Request.from_token_and_callback(access_token, http_method='POST',
                                                                    http_url=TEST_SERVER + '/XAPI/statements', parameters=post_oauth_header_resource_params_dict)
        post_signature_method2 = oauth.SignatureMethod_HMAC_SHA1()
        post_signature2 = post_signature_method2.sign(
            post_oauth_request2, self.consumer, access_token)
        sig = oauth_header_resource_params.replace(
            '"%s"' % post_signature, '"%s"' % post_signature2)
        new_oauth_headers = sig.replace(
            'oauth_nonce="resource_nonce"', 'oauth_nonce="post_differ_nonce"')

        resp = self.client.post(TEST_SERVER + '/XAPI/statements', data=stmt2, content_type="application/json",
                                Authorization=new_oauth_headers, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 200)

    def test_update_activity_with_oauth_containing_user(self):
        url = 'http://testserver/XAPI/statements'
        guid = str(uuid.uuid1())
        stmt_data = {"id": guid, "actor": {"objectType": "Agent",
                                           "mbox": "mailto:bob@bob.com", "name": "bob"}, "verb": {"id": "http://example.com/verbs/passed",
                                                                                                  "display": {"en-US": "passed"}}, "object": {"id": "test://test/define/scope"}}
        stmt_post = self.client.post(reverse('lrs:statements'), json.dumps(stmt_data), content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        # build stmt data and path
        put_guid = str(uuid.uuid1())
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:bill@bill.com", "name": "bill"},
                           "verb": {"id": "http://example.com/verbs/accessed", "display": {"en-US": "accessed"}},
                           "object": {"id": "test://test/define/scope",
                                      'definition': {'name': {'en-US': 'testname', 'en-GB': 'altname'},
                                                     'description': {'en-US': 'testdesc', 'en-GB': 'altdesc'}, 'type': 'type:course',
                                                     'interactionType': 'other', 'correctResponsesPattern': []}}})

        param = {"statementId": put_guid}
        path = "%s?%s" % (url, urllib.parse.urlencode(param))

        # START PUT STMT
        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type='statements/write statements/read define')

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='PUT',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        # Put statements - should update existing activity since jane is in
        # oauth group
        resp = self.client.put(path, data=stmt, content_type="application/json",
                               Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(resp.status_code, 204)
        acts = Activity.objects.all()
        self.assertEqual(len(acts), 1)
        act = acts[0].return_activity_with_lang_format()
        self.assertEqual(act['id'], 'test://test/define/scope')
        self.assertIn('definition', act)

    def test_update_activity_created_with_oauth(self):
        url = 'http://testserver/XAPI/statements'

        # build stmt data and path
        put_guid = str(uuid.uuid1())
        stmt = {"actor": {"objectType": "Agent",
                          "mbox": "mailto:bob@bob.com", "name": "bob"}, "verb": {"id": "http://example.com/verbs/passed",
                                                                                 "display": {"en-US": "passed"}}, "object": {"id": "test://test/define/scope"}}
        param = {"statementId": put_guid}
        path = "%s?%s" % (url, urllib.parse.urlencode(param))

        # START PUT STMT
        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type='statements/write statements/read define')

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='PUT',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        # Put statements - should update existing activity since jane is in
        # oauth group
        resp = self.client.put(path, data=stmt, content_type="application/json",
                               Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 204)
        # ==================================================================

        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:bill@bill.com", "name": "bill"},
                           "verb": {"id": "http://example.com/verbs/accessed", "display": {"en-US": "accessed"}},
                           "object": {"id": "test://test/define/scope",
                                      'definition': {'name': {'en-US': 'testname', 'en-GB': 'altname'},
                                                     'description': {'en-US': 'testdesc', 'en-GB': 'altdesc'}, 'type': 'type:course',
                                                     'interactionType': 'other', 'correctResponsesPattern': []}}})
        stmt_post = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(stmt_post.status_code, 200)

        acts = Activity.objects.all()
        self.assertEqual(len(acts), 1)
        act = acts[0].return_activity_with_lang_format()
        self.assertEqual(act['id'], 'test://test/define/scope')
        self.assertIn('definition', act)

    def test_multiple_client_get(self):
        url = 'http://testserver/XAPI/statements'

        # build stmt data and path
        put_guid = str(uuid.uuid1())
        stmt = {"actor": {"objectType": "Agent",
                          "mbox": "mailto:bob@bob.com", "name": "bob"}, "verb": {"id": "http://example.com/verbs/passed",
                                                                                 "display": {"en-US": "passed"}}, "object": {"id": "test://test/define/scope"}}
        param = {"statementId": put_guid}
        path = "%s?%s" % (url, urllib.parse.urlencode(param))

        # START PUT STMT
        oauth_header_resource_params, access_token = self.oauth_handshake(
            scope_type='statements/write statements/read define')

        # from_token_and_callback takes a dictionary
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        # Create oauth request and add signature
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='PUT',
                                                              http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(
            oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        # Put statements - should update existing activity since jane is in
        # oauth group
        resp = self.client.put(path, data=stmt, content_type="application/json",
                               Authorization=oauth_header_resource_params, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 204)
        # ==================================================================

        # build stmt data and path
        put_guid2 = str(uuid.uuid1())
        stmt2 = {"actor": {"objectType": "Agent",
                           "mbox": "mailto:billbob@bob.com", "name": "bob"}, "verb": {"id": "http://example.com/verbs/passed",
                                                                                      "display": {"en-US": "passed"}}, "object": {"id": "test://mult-test"}}
        param2 = {"statementId": put_guid2}
        path2 = "%s?%s" % (url, urllib.parse.urlencode(param2))

        # START PUT STMT
        oauth_header_resource_params2, access_token2 = self.oauth_handshake(
            scope_type='statements/write define', consumer=self.consumer2jane)

        # from_token_and_callback takes a dictionary
        param_list2 = oauth_header_resource_params2.split(",")
        oauth_header_resource_params_dict2 = {}
        for p in param_list2:
            item = p.split("=")
            oauth_header_resource_params_dict2[
                str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to
        # from_token_and_callback
        del oauth_header_resource_params_dict2['OAuth realm']

        # Create oauth request and add signature
        oauth_request2 = oauth.Request.from_token_and_callback(access_token2, http_method='PUT',
                                                               http_url=path2, parameters=oauth_header_resource_params_dict2)
        signature_method2 = oauth.SignatureMethod_HMAC_SHA1()
        signature2 = signature_method2.sign(
            oauth_request2, self.consumer2jane, access_token2)
        oauth_header_resource_params2 += ',oauth_signature="%s"' % signature2

        # Put statements - should update existing activity since jane is in
        # oauth group
        resp2 = self.client.put(path2, data=stmt2, content_type="application/json",
                                Authorization=oauth_header_resource_params2, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp2.status_code, 204)
        # ==================================================================

        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:bill@bill.com", "name": "bill"},
                           "verb": {"id": "http://example.com/verbs/accessed", "display": {"en-US": "accessed"}},
                           "object": {"id": "test://test/define/scope",
                                      'definition': {'name': {'en-US': 'testname', 'en-GB': 'altname'},
                                                     'description': {'en-US': 'testdesc', 'en-GB': 'altdesc'}, 'type': 'type:course',
                                                     'interactionType': 'other', 'correctResponsesPattern': []}}})
        stmt_post = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                     Authorization=self.jane_auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(stmt_post.status_code, 200)
        # ==================================================================

        stmt_get = self.client.get(reverse(
            'lrs:statements'), X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.jane_auth)
        self.assertEqual(stmt_get.status_code, 200)
        content = json.loads(stmt_get.content)
        self.assertEqual(len(content['statements']), 3)

        jane_clients = Consumer.objects.filter(user=self.user)
        self.assertEqual(len(jane_clients), 2)
