import time
import urllib
import json
import datetime
from urlparse import parse_qs, urlparse

from django.conf import settings
from django.test.client import RequestFactory

import oauth2 as oauth

from oauth_provider.tests.auth import BaseOAuthTestCase, METHOD_AUTHORIZATION_HEADER
from oauth_provider.models import Token, Scope
from oauth_provider import utils, responses
from oauth_provider.store import store as oauth_provider_store


class OAuthTestsBug10(BaseOAuthTestCase):
    """
    See https://code.welldev.org/django-oauth-plus/issue/10/malformed-callback-url-when-user-denies
    """
    def test_Request_token_request_succeeds_with_valid_request_token_parameters(self):
        response = self._request_token()
        token = self.request_token

        self.assertEqual(token.callback,
                         self.callback_token)
        self.assertEqual(
            token.callback_confirmed,
            self.callback_confirmed)

    def test_Requesting_user_authorization_fails_when_user_denies_authorization(self):
        self._request_token()
        self.c.login(username=self.username, password=self.password)
        parameters = authorization_parameters = {'oauth_token': self.request_token.key}
        response = self.c.get("/oauth/authorize/", parameters)
        self.assertEqual(
            response.status_code,
            200)

        # fake access not granted by the user (set session parameter again)
        authorization_parameters['authorize_access'] = False
        response = self.c.post("/oauth/authorize/", authorization_parameters)
        self.assertEqual(
            response.status_code,
            302)
        self.assertEqual('http://printer.example.com/request_token_ready?error=Access+not+granted+by+user.', response['Location'])
        self.c.logout()

class OAuthOutOfBoundTests(BaseOAuthTestCase):
    def test_Requesting_user_authorization_succeeds_when_oob(self):
        self._request_token(oauth_callback="oob")

        self.c.login(username=self.username, password=self.password)
        parameters = self.authorization_parameters = {'oauth_token': self.request_token.key}
        response = self.c.get("/oauth/authorize/", parameters)

        self.assertEqual(
            response.status_code,
            200)

class OauthTestIssue24(BaseOAuthTestCase):
    """
    See https://bitbucket.org/david/django-oauth-plus/issue/24/utilspy-initialize_server_request-should
    """
    def setUp(self):
        super(OauthTestIssue24, self).setUp()

        #setting the access key/secret to made-up strings
        self.access_token = Token(
            key="key",
            secret="secret",
            consumer=self.consumer,
            user=self.jane,
            token_type=2,
            scope=self.scope
        )
        self.access_token.save()


    def __make_querystring_with_HMAC_SHA1(self, http_method, path, data, content_type):
        """
        Utility method for creating a request which is signed using HMAC_SHA1 method
        """
        consumer = oauth.Consumer(key=self.CONSUMER_KEY, secret=self.CONSUMER_SECRET)
        token = oauth.Token(key=self.access_token.key, secret=self.access_token.secret)

        url = "http://testserver:80" + path

        #if data is json, we want it in the body, else as parameters (i.e. queryparams on get)
        parameters=None
        body = ""
        if content_type=="application/json":
            body = data
        else:
            parameters = data

        request = oauth.Request.from_consumer_and_token(
            consumer=consumer,
            token=token,
            http_method=http_method,
            http_url=url,
            parameters=parameters,
            body=body
        )

        # Sign the request.
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        request.sign_request(signature_method, consumer, token)
        return request.to_url()

    def test_that_initialize_server_request_when_custom_content_type(self):
        """Chceck if post data is not included in params when constent type
        is not application/x-www-form-urlencoded. It would cause problems only when signature method is
        HMAC-SHA1
         """

        data = json.dumps({"data": {"foo": "bar"}})
        content_type = "application/json"
        querystring = self.__make_querystring_with_HMAC_SHA1("POST", "/path/to/post", data, content_type)

        #we're just using the request, don't bother faking sending it
        rf = RequestFactory()
        request = rf.post(querystring, data, content_type)

        #this is basically a "remake" of the relevant parts of OAuthAuthentication in django-rest-framework
        oauth_request = utils.get_oauth_request(request)

        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = oauth_provider_store.get_consumer(request, oauth_request, consumer_key)

        token_param = oauth_request.get_parameter('oauth_token')
        token = oauth_provider_store.get_access_token(request, oauth_request, consumer, token_param)

        oauth_server, oauth_request = utils.initialize_server_request(request)

        #check that this does not throw an oauth.Error
        oauth_server.verify_request(oauth_request, consumer, token)

    def test_post_using_in_authorization_header_and_PLAINTEXT(self):
        self._request_token()
        self._authorize_and_access_token_using_form()

        parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_signature_method': "PLAINTEXT",
            'oauth_version': "1.0",
            'oauth_token': self.ACCESS_TOKEN_KEY,
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': str(int(time.time()))+"nonce",
            'oauth_signature': "%s&%s" % (self.CONSUMER_SECRET, self.ACCESS_TOKEN_SECRET),
            }
        header = self._get_http_authorization_header(parameters)
        response = self.c.post("/oauth/photo/", HTTP_AUTHORIZATION=header)

        self.assertEqual(response.status_code, 200)

    def test_post_using_auth_in_post_body_and_PLAINTEXT(self):
        """Check if auth works when authorization data is in post body when
        content type is pplication/x-www-form-urlencoded
        """
        self._request_token()
        self._authorize_and_access_token_using_form()

        parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_signature_method': "PLAINTEXT",
            'oauth_version': "1.0",
            'oauth_token': self.ACCESS_TOKEN_KEY,
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': str(int(time.time()))+"nonce",
            'oauth_signature': "%s&%s" % (self.CONSUMER_SECRET, self.ACCESS_TOKEN_SECRET),
            "additional_data": "whoop" # additional data
            }
        response = self.c.post("/oauth/photo/", urllib.urlencode(parameters, True),
            content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 200)

    def test_post_using_auth_in_header_with_content_type_json_and_PLAINTEXT(self):
        self._request_token()
        self._authorize_and_access_token_using_form()

        parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_signature_method': "PLAINTEXT",
            'oauth_version': "1.0",
            'oauth_token': self.ACCESS_TOKEN_KEY,
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': str(int(time.time()))+"nonce",
            'oauth_signature': "%s&%s" % (self.CONSUMER_SECRET, self.ACCESS_TOKEN_SECRET),
            }

        header = self._get_http_authorization_header(parameters)
        response = self.c.post("/oauth/photo/", HTTP_AUTHORIZATION=header, CONTENT_TYPE="application/json")

        self.assertEqual(response.status_code, 200)

    def test_post_using_auth_in_body_content_type_and_application_x_www_form_urlencoded(self):
        """Opposite of test_that_initialize_server_request_when_custom_content_type,
        If content type is application/x-www-form-urlencoded, post data should be added to params,
        and it affects signature
        """
        self._request_token()
        self._authorize_and_access_token_using_form()

        data={"foo": "bar"}
        content_type = "application/x-www-form-urlencoded"
        querystring = self.__make_querystring_with_HMAC_SHA1("POST", "/path/to/post", data, content_type)

        #we're just using the request, don't bother faking sending it
        rf = RequestFactory()
        request = rf.post(querystring, urllib.urlencode(data), content_type)

        #this is basically a "remake" of the relevant parts of OAuthAuthentication in django-rest-framework
        oauth_request = utils.get_oauth_request(request)

        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = oauth_provider_store.get_consumer(request, oauth_request, consumer_key)

        token_param = oauth_request.get_parameter('oauth_token')
        token = oauth_provider_store.get_access_token(request, oauth_request, consumer, token_param)

        oauth_server, oauth_request = utils.initialize_server_request(request)

        #check that this does not throw an oauth.Error
        oauth_server.verify_request(oauth_request, consumer, token)


class OAuthTestsBug2UrlParseNonHttpScheme(BaseOAuthTestCase):
    def test_non_http_url_callback_scheme(self):

        # @vmihailenco callback example
        self._request_token(oauth_callback='ftp://fnaffgdfmcfbjiifjkhbfbnjljaabiaj.com/chrome_ex_oauth.html?q=1')

        self.c.login(username=self.username, password=self.password)
        parameters = self.authorization_parameters = {'oauth_token': self.request_token.key}
        response = self.c.get("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 200)

        # fill form (authorize us)
        parameters['authorize_access'] = 1
        response = self.c.post("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 302)

        # assert query part of url is not malformed
        assert "?q=1&" in response["Location"]

class OAuthTestIssue41XForwardedProto(BaseOAuthTestCase):

    def setUp(self):
        super(OAuthTestIssue41XForwardedProto, self).setUp()
        self._request_token(METHOD_AUTHORIZATION_HEADER)
        self._authorize_and_access_token_using_form(METHOD_AUTHORIZATION_HEADER)
        print

    def _make_GET_auth_header(self, url):
        token = oauth.Token(self.ACCESS_TOKEN_KEY, self.ACCESS_TOKEN_SECRET)
        consumer = oauth.Consumer(self.CONSUMER_KEY, self.CONSUMER_SECRET)

        request = oauth.Request.from_consumer_and_token(
            consumer=consumer,
            token=token,
            http_method="GET",
            http_url=url,
        )

        # Sign the request.
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        request.sign_request(signature_method, consumer, token)
        return request.to_header()["Authorization"]

    def test_when_same_protocol(self):
        """Test that signature vierifies when protocol used for signing is same as used in request
        """
        url = "http://testserver/oauth/none/"
        kwargs = {
            "HTTP_AUTHORIZATION": self._make_GET_auth_header(url),
        }
        response = self.c.get(url.replace('http', 'https'), **kwargs)
        self.assertEqual(response.status_code, 200)

        url = "https://testserver:80/oauth/none/"
        kwargs = {
            # this tells django test client to pretend it was https request
            'wsgi.url_scheme': "https",
            "HTTP_AUTHORIZATION": self._make_GET_auth_header(url),
        }
        response = self.c.get(url, **kwargs)
        self.assertEqual(response.status_code, 200)


    def test_when_protocol_mismatch(self):
        """Test that signature does not vierifies when protocol is diffrent from that which was used for signing request
        """
        url = "https://testserver:80/oauth/none/"
        kwargs = {
            'wsgi.url_scheme': "http",
            "HTTP_AUTHORIZATION": self._make_GET_auth_header(url),
        }
        response = self.c.get(url.replace('https', 'http'), **kwargs)
        assert response == responses.COULD_NOT_VERIFY_OAUTH_REQUEST_RESPONSE
        self.assertEqual(response.status_code, 401)

        url = "http://testserver:80/oauth/none/"
        kwargs = {
            # this tells django test client to pretend it was https request
            'wsgi.url_scheme': "https",
            "HTTP_AUTHORIZATION": self._make_GET_auth_header(url),
        }
        response = self.c.get(url.replace('http', 'https'), **kwargs)
        assert response == responses.COULD_NOT_VERIFY_OAUTH_REQUEST_RESPONSE
        self.assertEqual(response.status_code, 401)

    def test_when_x_forwarded_proto_header_has_valid_protocol(self):
        """Test that signature verifies when X-Forwarded-Proto HTTP header has same protocol as one that was used for signing request
        """
        url = "https://testserver/oauth/none/"
        kwargs = {
            'wsgi.url_scheme': "http",
            'HTTP_AUTHORIZATION': self._make_GET_auth_header(url),
            'HTTP_X_FORWARDED_PROTO': 'https',
        }
        response = self.c.get(url.replace('https', 'http'), **kwargs)
        self.assertEqual(response.status_code, 200)


        url = "http://testserver/oauth/none/"
        kwargs = {
            'wsgi.url_scheme': "https",
            "HTTP_AUTHORIZATION": self._make_GET_auth_header(url),
            "HTTP_X_FORWARDED_PROTO": "http",
        }

        response = self.c.get(url.replace('http', 'https'), **kwargs)
        self.assertEqual(response.status_code, 200)


class OAuthTestIssue16NoncesCheckedAgainstTimestamp(BaseOAuthTestCase):
    def test_timestamp_ok(self):
        self._request_token()
        self._authorize_and_access_token_using_form()

        parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_signature_method': "PLAINTEXT",
            'oauth_version': "1.0",
            'oauth_token': self.ACCESS_TOKEN_KEY,
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': str(int(time.time()))+"nonce1",
            'oauth_signature': "%s&%s" % (self.CONSUMER_SECRET, self.ACCESS_TOKEN_SECRET),
            }

        response = self.c.get("/oauth/photo/", parameters)

        self.assertEqual(response.status_code, 200)

    def test_timestamp_repeated_nonce(self):
        self._request_token()
        self._authorize_and_access_token_using_form()

        timestamp = str(int(time.time()))
        nonce = timestamp + "nonce"
        parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_signature_method': "PLAINTEXT",
            'oauth_version': "1.0",
            'oauth_token': self.ACCESS_TOKEN_KEY,
            'oauth_timestamp': timestamp,
            'oauth_nonce': nonce,
            'oauth_signature': "%s&%s" % (self.CONSUMER_SECRET, self.ACCESS_TOKEN_SECRET),
            }

        response = self.c.get("/oauth/photo/", parameters)
        self.assertEqual(response.status_code, 200)

        response = self.c.get("/oauth/photo/", parameters)
        self.assertEqual(response.status_code, 401)

    def test_timestamp_old_nonce(self):
        self._request_token()
        self._authorize_and_access_token_using_form()

        #make this nonce older
        timestamp = str(int(datetime.datetime.now().strftime("%s")) - (settings.OAUTH_NONCE_VALID_PERIOD + 1))
        nonce = timestamp + "nonce"
        parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_signature_method': "PLAINTEXT",
            'oauth_version': "1.0",
            'oauth_token': self.ACCESS_TOKEN_KEY,
            'oauth_timestamp': timestamp,
            'oauth_nonce': nonce,
            'oauth_signature': "%s&%s" % (self.CONSUMER_SECRET, self.ACCESS_TOKEN_SECRET),
            }

        response = self.c.get("/oauth/photo/", parameters)
        self.assertEqual(response.status_code, 401)


class OAuthTestIssue39(BaseOAuthTestCase):
    """
    See https://bitbucket.org/david/django-oauth-plus/issue/39/request-token-scope-unused.
    """
    def setUp(self):
        super(OAuthTestIssue39, self).setUp()
        Scope.objects.create(name='scope1')
        Scope.objects.create(name='scope2')

    def test_different_token_scopes(self):
        self._request_token(scope='scope1')
        # Authorization code below copied from BaseOAuthTestCase
        self.c.login(username=self.username, password=self.password)
        parameters = self.authorization_parameters = {'oauth_token': self.request_token.key}
        response = self.c.get("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 200)

        # fill form (authorize us)
        parameters['authorize_access'] = 1
        response = self.c.post("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 302)

        # finally access authorized access_token
        oauth_verifier = parse_qs(urlparse(response['Location']).query)['oauth_verifier'][0]

        # logout to ensure that will not authorize with session
        self.c.logout()
        # Changed line - change the scope of access token
        # access token's scope should be same as request token
        self._access_token(oauth_verifier=oauth_verifier, oauth_token=self.request_token.key, scope='scope2')

        access_token = Token.objects.get(key=self.ACCESS_TOKEN_KEY)
        self.assertEqual(access_token.scope.name, 'scope1')


class OAuthTestIssue44PostRequestBodyInSignature(BaseOAuthTestCase):
    def test_POST_with_x_www_form_urlencoded_body_params_and_auth_header(self):
        """Test issue when user's request has authorization header and uses
        application/x-www-form-urlencoded content type with some
        request body parameters.

        note: In this case both POST and GET parameters should be included in
        signature base string, so we test GET and POST together
        note: behaviour defined in http://tools.ietf.org/html/rfc5849#section-3.4.1.3.1
        """
        # get valid access token
        self._request_token()
        self._authorize_and_access_token_using_form()

        # init request params and headers
        get_params = {"foo": "bar"}
        body_params = {"some": "param", "other": "param"}
        content_type = "application/x-www-form-urlencoded"
        header = self._make_auth_header_with_HMAC_SHA1('post', "/oauth/photo/", get_params, body_params, True)

        body = urllib.urlencode(body_params)

        response = self.c.post(
            # this is workaround to have both POST & GET params in this request
            "/oauth/photo/?%s" % urllib.urlencode(get_params),
            data=body,
            HTTP_AUTHORIZATION=header["Authorization"],
            content_type=content_type
        )

        self.assertEqual(response.status_code, 200)


    def test_POST_with_x_www_form_urlencoded_body_params_and_auth_header_unauthorized(self):
        """Test issue when user's request has authorization header and uses
        application/x-www-form-urlencoded content type with some
        request body parameters, but signature was generated without body
        params.
        """
        # get valid access token
        self._request_token()
        self._authorize_and_access_token_using_form()

        # init request params and headers
        get_params = {"foo": "bar"}
        body_params = {"some": "param", "other": "param"}
        content_type = "application/x-www-form-urlencoded"
        header = self._make_auth_header_with_HMAC_SHA1('post', "/oauth/photo/", get_params, {}, True)

        body = urllib.urlencode(body_params)

        response = self.c.post(
            # this is workaround to have both POST & GET params in this request
            "/oauth/photo/?%s" % urllib.urlencode(get_params),
            data=body,
            HTTP_AUTHORIZATION=header["Authorization"],
            content_type=content_type
        )

        self.assertEqual(response.status_code, 401)

    def _make_auth_header_with_HMAC_SHA1(self, http_method, path, get_params, body_params, is_form_encoded):
        """make auth header, take in consideration both get and post body_params
        """
        consumer = oauth.Consumer(key=self.CONSUMER_KEY, secret=self.CONSUMER_SECRET)
        token = oauth.Token(key=self.ACCESS_TOKEN_KEY, secret=self.ACCESS_TOKEN_SECRET)

        url = "http://testserver:80" + path

        body = urllib.urlencode(body_params)

        params = {}
        params.update(get_params)
        params.update(body_params)

        request = oauth.Request.from_consumer_and_token(
            consumer=consumer, token=token,
            http_method=http_method, http_url=url,
            is_form_encoded=is_form_encoded,
            body=body,
            # it seems that body parameter isn't enough to have body params
            # in signature base string
            parameters=params
        )

        # Sign the request.
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        request.sign_request(signature_method, consumer, token)
        return request.to_header()