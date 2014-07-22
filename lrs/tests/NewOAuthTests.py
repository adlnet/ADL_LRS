import uuid
import json
import urllib
import os
import base64
import re
import time
import oauth2 as oauth
from django.contrib.auth.models import User
from django.conf import settings
from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import views, models, forms
from lrs.objects.StatementManager import StatementManager
from oauth_provider.models import Consumer, Token, Nonce

# Django client uses testserver
TEST_SERVER = 'http://testserver'

class NewOAuthTests(TestCase):
    @classmethod
    def setUpClass(cls):
        print "\n%s" % __name__

    def setUp(self):
        if not settings.OAUTH_ENABLED:
            settings.OAUTH_ENABLED = True

        # Create a user
        self.user = User.objects.create_user('jane', 'jane@example.com', 'toto')
        user = self.client.login(username='jane', password='toto')

        #Register a consumer
        self.name = "test jane client"
        self.desc = "test jane client desc"
        form = {"name":self.name, "description":self.desc, "scopes":"all"}
        response = self.client.post(reverse(views.reg_client),form, X_Experience_API_Version="1.0.0")
        self.consumer = Consumer.objects.get(name=self.name)
        self.client.logout()

        # Create a user
        self.user2 = User.objects.create_user('dick', 'dick@example.com', 'lassie')
        user2 = self.client.login(username='dick', password='lassie')

        #Register a consumer
        self.name2 = "test dick client"
        self.desc2 = "test dick client desc"
        form2 = {"name":self.name2, "description":self.desc2, "scopes":"all"}
        response2 = self.client.post(reverse(views.reg_client),form2, X_Experience_API_Version="1.0.0")
        self.consumer2 = Consumer.objects.get(name=self.name2)
        self.client.logout()
    
    def tearDown(self):
        if settings.OAUTH_ENABLED:
            settings.OAUTH_ENABLED = False
        # Delete everything
        Token.objects.all().delete()
        Consumer.objects.all().delete()
        Nonce.objects.all().delete()
        User.objects.all().delete()

        attach_folder_path = os.path.join(settings.MEDIA_ROOT, "activity_state")
        for the_file in os.listdir(attach_folder_path):
            file_path = os.path.join(attach_folder_path, the_file)
            try:
                os.unlink(file_path)
            except Exception, e:
                raise e

    def test_request_token_missing_headers(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        # Missing signature method
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))
        
        # Make string params into dictionary for from_consumer_and_token function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')

        # Create OAuth request and signature
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        
        # Append signature to string headers
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        resp = self.client.get(request_token_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.content, 'Invalid request parameters.')

    def test_request_token_unsupported_headers(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "this_is_not_good=\"blah\","\
               "oauth_signature_method=\"HMAC-SHA1\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token function        
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')

        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        resp = self.client.get(request_token_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.content, 'Invalid request parameters.')

    def test_request_token_duplicated_headers(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"HMAC-SHA1\","\
               "oauth_signature_method=\"HMAC-SHA1\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token function        
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')

        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        resp = self.client.get(request_token_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.content, 'Invalid request parameters.')

    def test_request_token_unsupported_signature_method(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"unsupported\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token function        
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')

        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        resp = self.client.get(request_token_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.content, 'Invalid request parameters.')

    def test_request_token_invalid_consumer_credentials(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"unsupported\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % ("aaaaaaaaaaaaaa",str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token function        
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')

        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        resp = self.client.get(request_token_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.content, 'Invalid request parameters.')

    def test_request_token_unknown_scope(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"

        # passing scope as form param instead of in query string in this instance
        form_data = {
            'scope':'DNE',
        }

        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"HMAC-SHA1\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')

        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=dict(oauth_header_request_token_params_dict.items()+form_data.items()))
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, data=form_data, X_Experience_API_Version="1.0.0")

        self.assertEqual(request_resp.status_code, 401)
        self.assertEqual(request_resp.content, 'Could not verify OAuth request.')

    def test_request_token_wrong_scope(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"

        # passing scope as form param instead of in query string in this instance
        form_data = {
            'scope':'all',
        }

        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"HMAC-SHA1\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')

        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=dict(oauth_header_request_token_params_dict.items()+form_data.items()))
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, data=form_data, X_Experience_API_Version="1.0.0")

        self.assertEqual(request_resp.status_code, 401)
        self.assertEqual(request_resp.content, 'Could not verify OAuth request.')

    def test_request_token_same_nonce(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"HMAC-SHA1\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token function
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)


        # Header params we're passing in
        oauth_header_request_token_params2 = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"HMAC-SHA1\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make string params into dictionary for from_consumer_and_token function
        request_token_param_list2 = oauth_header_request_token_params2.split(",")
        oauth_header_request_token_params_dict2 = {}
        for p in request_token_param_list2:
            item = p.split("=")
            oauth_header_request_token_params_dict2[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict2['OAuth realm']

        # add scope to the existing params
        oauth_request2 = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict2)
        
        # create signature and add it to the header params
        signature_method2 = oauth.SignatureMethod_HMAC_SHA1()
        signature2 = signature_method.sign(oauth_request2, self.consumer, None)
        oauth_header_request_token_params2 = oauth_header_request_token_params2 + ",oauth_signature=%s" % signature2
        
        request_resp2 = self.client.get(request_token_path, Authorization=oauth_header_request_token_params2, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp2.status_code, 401)

    def test_request_token_no_scope(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"HMAC-SHA1\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)

    def test_request_token_scope_in_form(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        # passing scope as form param instead of in query string in this instance
        form_data = {
            'scope':'all',
            'consumer_name':'new_client'
        }

        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"HMAC-SHA1\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='POST',
            http_url=request_token_path, parameters=dict(oauth_header_request_token_params_dict.items()+form_data.items()))
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()

        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        # By default django's test client POSTs as multipart. We want form
        request_resp = self.client.post(request_token_path, Authorization=oauth_header_request_token_params, data=form_data,
            X_Experience_API_Version="1.0.0", content_type="application/x-www-form-urlencoded")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)

    def test_request_token_scope_in_qs(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"

        param = {
                    'scope':'all',
                    'consumer_name':'new_client'
                }
        request_token_path = "%s?%s" % (request_token_path, urllib.urlencode(param)) 
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"HMAC-SHA1\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)

    def test_request_token_plaintext(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"

        param = {
                    'scope':'all',
                    'consumer_name':'new_client'
                }
        request_token_path = "%s?%s" % (request_token_path, urllib.urlencode(param)) 
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)

    def test_request_token_rsa_sha1(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"

        param = {
                    'scope':'all',
                    'consumer_name':'new_client'
                }
        request_token_path = "%s?%s" % (request_token_path, urllib.urlencode(param)) 
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"RSA-SHA1\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_RSA_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)

    def test_request_token_wrong_oauth_version(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"

        param = {
                    'scope':'all',
                    'consumer_name':'new_client'
                }
        request_token_path = "%s?%s" % (request_token_path, urllib.urlencode(param)) 
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.1\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 401)

    def test_request_token_wrong_signature(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"

        param = {
                    'scope':'all',
                    'consumer_name':'new_client'
                }
        request_token_path = "%s?%s" % (request_token_path, urllib.urlencode(param)) 
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.1\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % "wrongsignature"
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 401)


    def test_auth_correct(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        param = {
                    'scope':'all',
                    'consumer_name':'new_client'
                }
        request_token_path = "%s?%s" % (request_token_path, urllib.urlencode(param)) 
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/access_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)

        # Test AUTHORIZE
        authorize_path = TEST_SERVER +"/XAPI/OAuth/authorize/"
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (authorize_path, urllib.urlencode(param)) 

        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn('http://testserver/XAPI/accounts/login?next=/XAPI/OAuth/authorize/%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])    
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
        
        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = token.key

        auth_post = self.client.post("/XAPI/OAuth/authorize/", data, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_post.status_code, 302)
        # Check if oauth_verifier and oauth_token are returned
        self.assertIn('http://example.com/access_token_ready?oauth_verifier=', auth_post['Location'])
        self.assertIn('oauth_token=', auth_post['Location'])
        access_token = Token.objects.get(consumer=self.consumer)
        self.assertIn(access_token.key, auth_post['Location'])
        self.assertEqual(access_token.is_approved, True)      

    def test_auth_scope_up(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        param = {
                    'scope':'statements/read',
                    'consumer_name':'new_client'
                }
        request_token_path = "%s?%s" % (request_token_path, urllib.urlencode(param)) 
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/access_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)

        # Test AUTHORIZE
        authorize_path = TEST_SERVER +"/XAPI/OAuth/authorize/"
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (authorize_path, urllib.urlencode(param)) 

        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn('http://testserver/XAPI/accounts/login?next=/XAPI/OAuth/authorize/%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])    
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
        
        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = token.key
        data['scopes'] = ['all']

        auth_post = self.client.post("/XAPI/OAuth/authorize/", data, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_post.status_code, 401)
        self.assertEqual(auth_post.content, 'Action not allowed.')

    def test_auth_wrong_auth(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        param = {
                    'scope':'statements/read',
                    'consumer_name':'new_client'
                }
        request_token_path = "%s?%s" % (request_token_path, urllib.urlencode(param)) 
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/access_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)

        # Test AUTHORIZE
        authorize_path = TEST_SERVER +"/XAPI/OAuth/authorize/"
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (authorize_path, urllib.urlencode(param)) 

        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn('http://testserver/XAPI/accounts/login?next=/XAPI/OAuth/authorize/%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])    
        self.client.login(username='dick', password='lassie')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 403) # Show return/display OAuth authorized view
        self.assertEqual(auth_resp.content, 'Invalid user for this client.')

    def test_auth_no_scope_chosen(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        param = {
                    'scope':'statements/read',
                    'consumer_name':'new_client'
                }
        request_token_path = "%s?%s" % (request_token_path, urllib.urlencode(param)) 
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/access_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)

        # Test AUTHORIZE
        authorize_path = TEST_SERVER +"/XAPI/OAuth/authorize/"
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (authorize_path, urllib.urlencode(param)) 

        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn('http://testserver/XAPI/accounts/login?next=/XAPI/OAuth/authorize/%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])    
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
        
        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = token.key
        data['scopes'] = []

        auth_post = self.client.post("/XAPI/OAuth/authorize/", data, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_post.status_code, 401)
        self.assertEqual(auth_post.content, 'Action not allowed.')

    def test_access_token_invalid_token(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        param = {
                    'scope':'all',
                    'consumer_name':'new_client'
                }
        request_token_path = "%s?%s" % (request_token_path, urllib.urlencode(param)) 
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/access_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)

        # Test AUTHORIZE
        authorize_path = TEST_SERVER +"/XAPI/OAuth/authorize/"
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (authorize_path, urllib.urlencode(param)) 

        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn('http://testserver/XAPI/accounts/login?next=/XAPI/OAuth/authorize/%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])    
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
        
        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = token.key

        auth_post = self.client.post("/XAPI/OAuth/authorize/", data, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_post.status_code, 302)
        # Check if oauth_verifier and oauth_token are returned
        self.assertIn('http://example.com/access_token_ready?oauth_verifier=', auth_post['Location'])
        self.assertIn('oauth_token=', auth_post['Location'])
        access_token = Token.objects.get(consumer=self.consumer)
        self.assertIn(access_token.key, auth_post['Location'])
        self.assertEqual(access_token.is_approved, True)
        access_token.is_approved = False
        access_token.save()

        # Test ACCESS TOKEN
        access_token_path = TEST_SERVER + "/XAPI/OAuth/token/"
        oauth_header_access_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_signature=\"%s&%s\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"accessnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_verifier=\"%s\"" % (self.consumer.key,token.key,self.consumer.secret,token.secret,str(int(time.time())),token.verifier)

        access_resp = self.client.get(access_token_path, Authorization=oauth_header_access_params,
            X_Experience_API_Version="1.0.0")
        self.assertEqual(access_resp.status_code, 400)
        self.assertEqual(access_resp.content, "Request Token not approved by the user.")
    
    def test_access_token_access_resources(self):
        request_token_path = TEST_SERVER +"/XAPI/OAuth/initiate/"
        param = {
                    'scope':'all',
                    'consumer_name':'new_client'
                }
        request_token_path = "%s?%s" % (request_token_path, urllib.urlencode(param)) 
        # Header params we're passing in
        oauth_header_request_token_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"12345678\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/access_token_ready\"" % (self.consumer.key,str(int(time.time())))

        # Make the params into a dict to pass into from_consumer_and_token
        request_token_param_list = oauth_header_request_token_params.split(",")
        oauth_header_request_token_params_dict = {}
        for p in request_token_param_list:
            item = p.split("=")
            oauth_header_request_token_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # get_oauth_request in views ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_request_token_params_dict['OAuth realm']

        # add scope to the existing params
        oauth_request = oauth.Request.from_consumer_and_token(self.consumer, token=None, http_method='GET',
            http_url=request_token_path, parameters=oauth_header_request_token_params_dict)
        
        # create signature and add it to the header params
        signature_method = oauth.SignatureMethod_PLAINTEXT()
        signature = signature_method.sign(oauth_request, self.consumer, None)
        oauth_header_request_token_params = oauth_header_request_token_params + ",oauth_signature=%s" % signature
        
        request_resp = self.client.get(request_token_path, Authorization=oauth_header_request_token_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret', request_resp.content)
        self.assertIn('oauth_token', request_resp.content)
        self.assertIn('oauth_callback_confirmed', request_resp.content)
        token = Token.objects.get(consumer=self.consumer)

        # Test AUTHORIZE
        authorize_path = TEST_SERVER +"/XAPI/OAuth/authorize/"
        param = {'oauth_token': token.key}
        authorize_path = "%s?%s" % (authorize_path, urllib.urlencode(param)) 

        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn('http://testserver/XAPI/accounts/login?next=/XAPI/OAuth/authorize/%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])    
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        # After being redirected to login and logging in again, try get again
        auth_resp = self.client.get(authorize_path, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
        
        auth_form = auth_resp.context['form']
        data = auth_form.initial
        data['authorize_access'] = 1
        data['oauth_token'] = token.key

        auth_post = self.client.post("/XAPI/OAuth/authorize/", data, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_post.status_code, 302)
        # Check if oauth_verifier and oauth_token are returned
        self.assertIn('http://example.com/access_token_ready?oauth_verifier=', auth_post['Location'])
        self.assertIn('oauth_token=', auth_post['Location'])
        request_token = Token.objects.get(consumer=self.consumer)
        self.assertIn(request_token.key, auth_post['Location'])
        self.assertEqual(request_token.is_approved, True)

        # Test ACCESS TOKEN
        access_token_path = TEST_SERVER + "/XAPI/OAuth/token/"
        oauth_header_access_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_signature=\"%s&%s\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"87654321\","\
            "oauth_version=\"1.0\","\
            "oauth_verifier=\"%s\"" % (self.consumer.key,token.key,self.consumer.secret,request_token.secret,str(int(time.time())),request_token.verifier)

        access_resp = self.client.get(access_token_path, Authorization=oauth_header_access_params,
            X_Experience_API_Version="1.0.0")
        self.assertEqual(access_resp.status_code, 200)
        content = access_resp.content.split('&')
        access_token_secret = content[0].split('=')[1]
        access_token_key = content[1].split('=')[1]
        access_token = Token.objects.get(secret=access_token_secret, key=access_token_key)

        # Test ACCESS RESOURCE
        oauth_header_resource_params = "OAuth realm=\"test\", "\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"accessresourcenonce\","\
            "oauth_version=\"1.0\"" % (self.consumer.key, access_token.key, str(int(time.time())))

        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        path = TEST_SERVER + "/XAPI/statements"
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)

        # Create signature and add it to the headers
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path, Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)

    # def test_oauth_disabled(self):
    #     # Disable oauth
    #     if settings.OAUTH_ENABLED:
    #         settings.OAUTH_ENABLED = False

