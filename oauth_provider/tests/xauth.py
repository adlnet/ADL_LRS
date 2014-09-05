# -*- coding: utf-8 -*-
import time
import urllib
from urlparse import parse_qs

from oauth_provider.models import Scope
from oauth_provider.tests.auth import BaseOAuthTestCase, METHOD_URL_QUERY, METHOD_AUTHORIZATION_HEADER, METHOD_POST_REQUEST_BODY


class XAuthTestCase(BaseOAuthTestCase):
    def setUp(self):
        super(XAuthTestCase, self).setUp()
        self.consumer.xauth_allowed = True
        self.consumer.save()

    def _accesss_token(self, method=METHOD_URL_QUERY):
        parameters = {
            "oauth_consumer_key": self.CONSUMER_KEY,
            "oauth_consumer_secret": self.CONSUMER_SECRET,
            "oauth_nonce": "12981230918711",
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_signature': "%s&%s" % (self.CONSUMER_SECRET, ""),
            'oauth_timestamp': str(int(time.time())),
            'oauth_version': '1.0',

            'x_auth_mode': "client_auth",
            'x_auth_password': self.password,
            'x_auth_username': self.username,
        }

        if method==METHOD_AUTHORIZATION_HEADER:
            header = self._get_http_authorization_header(parameters)
            response = self.c.get("/oauth/access_token/", HTTP_AUTHORIZATION=header)
        elif method==METHOD_URL_QUERY:
            response = self.c.get("/oauth/access_token/", parameters)
        elif method==METHOD_POST_REQUEST_BODY:
            body = urllib.urlencode(parameters)
            response = self.c.post("/oauth/access_token/", body, content_type="application/x-www-form-urlencoded")
        else:
            raise NotImplementedError

        self.assertEqual(response.status_code, 200)
        response_params = parse_qs(response.content)

        self.ACCESS_TOKEN_KEY = response_params['oauth_token'][0]
        self.ACCESS_TOKEN_SECRET = response_params['oauth_token_secret'][0]

    def test_xauth(self):
        self._access_token(x_auth_mode="client_auth",
                           x_auth_password=self.password,
                           x_auth_username=self.username)

        assert self.ACCESS_TOKEN_KEY
        assert self.ACCESS_TOKEN_SECRET

    def test_xauth_using_email(self):
        self._access_token(x_auth_mode="client_auth",
                           x_auth_password=self.password,
                           x_auth_username=self.email)

        assert self.ACCESS_TOKEN_KEY
        assert self.ACCESS_TOKEN_SECRET