## -*- coding: utf-8 -*-
from pprint import pprint
import time
import urllib
from oauth_provider.models import Scope
from oauth_provider.tests.auth import BaseOAuthTestCase, METHOD_POST_REQUEST_BODY, METHOD_AUTHORIZATION_HEADER, METHOD_URL_QUERY


class OAuthTestOauthRequiredDecorator(BaseOAuthTestCase):
    def setUp(self):
        # create Scope 'all' for all requests without scope specified
        super(OAuthTestOauthRequiredDecorator, self).setUp()

    def _oauth_signed_get(self, url, method=METHOD_URL_QUERY):
        parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_signature_method': "PLAINTEXT",
            'oauth_version': "1.0",
            'oauth_token': self.ACCESS_TOKEN_KEY,
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': str(int(time.time()))+"nonce",
            'oauth_signature': "%s&%s" % (self.CONSUMER_SECRET, self.ACCESS_TOKEN_SECRET),
            "additional_data": "whoop",  # some additional data
            }

        if method==METHOD_AUTHORIZATION_HEADER:
            header = self._get_http_authorization_header(parameters)
            response = self.c.get(url, HTTP_AUTHORIZATION=header)
        elif method==METHOD_URL_QUERY:
            response = self.c.get(url, parameters)
        elif method==METHOD_POST_REQUEST_BODY:
            body = urllib.urlencode(parameters)
            response = self.c.post(url, body, content_type="application/x-www-form-urlencoded")
        else:
            raise NotImplementedError

        return response

    def test_resource_some_scope_view_authorized(self):
        """Tests view that was created using @oauth_required("some") decorator
        """
        #ensure there is a Scope object for this scope
        self.scope = Scope.objects.create(name="some")
        #set scope for requested token
        self._request_token(scope=self.scope.name)
        self._authorize_and_access_token_using_form()

        response = self._oauth_signed_get("/oauth/some/")
        self.assertEqual(response.status_code, 200)

    def test_scope_some_scope_view_not_authorized(self):
        """Tests that view created with @oauth_required("some") decorator won't give access
        when requested using token with different scope
        """
        self._request_token()
        self._authorize_and_access_token_using_form()

        response = self._oauth_signed_get("/oauth/some/")
        self.assertEqual(response.status_code, 401)

    def test_resource_None_view(self):
        """Tests that view created using @oauth_required decorator gives access
        when requested using token without scope specified
        """
        #request token without setting scope
        self._request_token()
        self._authorize_and_access_token_using_form()

        response = self._oauth_signed_get("/oauth/none/")
        self.assertEqual(response.status_code, 200)

    def test_resource_None_scope_view_not_authorized(self):
        """Tests that view created with @oauth_required decorator won't give access
        when requested using token with scope!="all"
        """
        #ensure there is a Scope object for this scope
        self.scope = Scope.objects.create(name="some_new_scope")
        self._request_token(scope=self.scope.name)
        self._authorize_and_access_token_using_form()

        response = self._oauth_signed_get("/oauth/some/")
        self.assertEqual(response.status_code, 401)

    def test_get_with_header_auth(self):
        #request token without setting scope
        self._request_token()
        self._authorize_and_access_token_using_form()

        response = self._oauth_signed_get("/oauth/none/", method=METHOD_AUTHORIZATION_HEADER)
        self.assertEqual(response.status_code, 200)

    def test_get_with_url_query_auth(self):
        #request token without setting scope
        self._request_token()
        self._authorize_and_access_token_using_form()

        response = self._oauth_signed_get("/oauth/none/", method=METHOD_URL_QUERY)
        self.assertEqual(response.status_code, 200)

    def test_get_with_request_body_auth(self):
        #request token without setting scope
        self._request_token()
        self._authorize_and_access_token_using_form()

        response = self._oauth_signed_get("/oauth/none/", method=METHOD_POST_REQUEST_BODY)
        self.assertEqual(response.status_code, 200)