# -*- coding: utf-8 -*-
import time
import urllib.request, urllib.parse, urllib.error
import re
from urllib.parse import parse_qs, urlparse
from django.test import TestCase, Client

import oauth2

from oauth_provider.models import Scope, Consumer, Token
from oauth_provider.compat import get_user_model

User = get_user_model()

METHOD_AUTHORIZATION_HEADER = 0
METHOD_POST_REQUEST_BODY = 1
METHOD_URL_QUERY = 2


class BaseOAuthTestCase(TestCase):

    def setUp(self):
        self.username = 'jane'
        self.password = 'toto'
        self.email = 'jane@example.com'
        self.jane = User.objects.create_user(
            self.username, self.email, self.password)
        self.scope = Scope.objects.create(name='photos', url='/oauth/photo/')

        self.CONSUMER_KEY = 'dpf43f3p2l4k3l03'
        self.CONSUMER_SECRET = 'kd94hf93k423kf44'

        consumer = self.consumer = Consumer(key=self.CONSUMER_KEY, secret=self.CONSUMER_SECRET,
                                            name='printer.example.com', user=self.jane)
        consumer.save()

        self.callback_token = self.callback = 'http://printer.example.com/request_token_ready'
        self.callback_confirmed = True
        self.c = Client()

    def _request_token(self, method=METHOD_URL_QUERY, **parameters_overriden):
        # The Consumer sends the following HTTP POST request to the
        # Service Provider:
        parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_signature': '%s&' % self.CONSUMER_SECRET,
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': 'requestnonce',
            'oauth_version': '1.0',
            'oauth_callback': self.callback,
            # 'scope': self.scope.name,  # custom argument to specify Protected Resource
        }
        parameters.update(parameters_overriden)

        if method == METHOD_AUTHORIZATION_HEADER:
            header = self._get_http_authorization_header(parameters)
            response = self.c.get("/oauth/request_token/",
                                  HTTP_AUTHORIZATION=header)
        elif method == METHOD_URL_QUERY:
            response = self.c.get("/oauth/request_token/", parameters)
        elif method == METHOD_POST_REQUEST_BODY:
            body = urllib.parse.urlencode(parameters)
            response = self.c.post(
                "/oauth/request_token/", body, content_type="application/x-www-form-urlencoded")
        else:
            raise NotImplementedError

        if response.status_code != 200:
            print(response)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            re.match(r'oauth_token_secret=[^&]+&oauth_token=[^&]+&oauth_callback_confirmed=true', response.content
                     ))

        token = self.request_token = list(Token.objects.all())[-1]
        self.assertTrue(token.key in response.content)
        self.assertTrue(token.secret in response.content)
        self.assertTrue(not self.request_token.is_approved)
        return response

    def _authorize_and_access_token_using_form(self, method=METHOD_URL_QUERY):
        self.c.login(username=self.username, password=self.password)
        parameters = self.authorization_parameters = {
            'oauth_token': self.request_token.key}
        response = self.c.get("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 200)

        # fill form (authorize us)
        parameters['authorize_access'] = 1
        response = self.c.post("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 302)

        # finally access authorized access_token
        oauth_verifier = parse_qs(urlparse(response['Location']).query)[
            'oauth_verifier'][0]

        # logout to ensure that will not authorize with session
        self.c.logout()

        self._access_token(oauth_verifier=oauth_verifier,
                           oauth_token=self.request_token.key)

    def _access_token(self, method=METHOD_URL_QUERY, **parameters_overriden):

        if hasattr(self, 'request_token'):
            oauth_signature = "%s&%s" % (
                self.CONSUMER_SECRET, self.request_token.secret)
        else:
            oauth_signature = "%s&" % (self.CONSUMER_SECRET)

        parameters = {
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_signature': oauth_signature,
            'oauth_consumer_key': self.CONSUMER_KEY,

            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': "12981230918711",

            'oauth_version': '1.0',
            'scope': self.scope.name,  # custom argument to specify Protected Resource
        }
        parameters.update(parameters_overriden)

        if method == METHOD_AUTHORIZATION_HEADER:
            header = self._get_http_authorization_header(parameters)
            response = self.c.get("/oauth/access_token/",
                                  HTTP_AUTHORIZATION=header)
        elif method == METHOD_URL_QUERY:
            response = self.c.get("/oauth/access_token/", parameters)
        elif method == METHOD_POST_REQUEST_BODY:
            body = urllib.parse.urlencode(parameters)
            response = self.c.post(
                "/oauth/access_token/", body, content_type="application/x-www-form-urlencoded")
        else:
            raise NotImplementedError

        self.assertEqual(response.status_code, 200)
        response_params = parse_qs(response.content)
        self.ACCESS_TOKEN_KEY = response_params['oauth_token'][0]
        self.ACCESS_TOKEN_SECRET = response_params['oauth_token_secret'][0]

    def _get_http_authorization_header(self, parameters):
        HEADERS = oauth2.Request("GET", parameters=parameters).to_header()
        authorization_header = HEADERS["Authorization"]
        # patch header with scope
        authorization_header += ", scope=%s" % self.scope.name
        return authorization_header


class TestOAuthDifferentAuthorizationMethods(BaseOAuthTestCase):

    def test_request_token_with_authorization_header(self):
        self._request_token(METHOD_AUTHORIZATION_HEADER)

    def test_request_token_with_url_query(self):
        self._request_token(METHOD_URL_QUERY)

    def test_request_token_with_post_request_body(self):
        self._request_token(METHOD_POST_REQUEST_BODY)

    def test_access_token_with_authorization_header(self):
        self._request_token(METHOD_AUTHORIZATION_HEADER)
        self._authorize_and_access_token_using_form(
            METHOD_AUTHORIZATION_HEADER)

    def test_access_token_with_url_query(self):
        self._request_token(METHOD_URL_QUERY)
        self._authorize_and_access_token_using_form(METHOD_URL_QUERY)

    def test_access_token_with_post_request_body(self):
        self._request_token(METHOD_POST_REQUEST_BODY)
        self._authorize_and_access_token_using_form(METHOD_POST_REQUEST_BODY)
