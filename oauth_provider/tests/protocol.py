import time
import cgi

import oauth2 as oauth

from django.test import Client

from oauth_provider.tests.auth import BaseOAuthTestCase
from oauth_provider.models import Token, Consumer, Scope
from oauth_provider.compat import get_user_model

User = get_user_model()


class ProtocolExample(BaseOAuthTestCase):
    """Set of tests, based on ProtocolExample document
    """
    def _last_created_request_token(self):
        return list(Token.objects.filter(token_type=Token.REQUEST))[-1]
    
    def _last_created_access_token(self):
        return list(Token.objects.filter(token_type=Token.ACCESS))[-1]
    
    def _update_token_from_db(self, request_token):
        """Get fresh copy of the token from the DB"""
        return Token.objects.get(key=request_token.key)

    def _make_request_token_parameters(self):
        return {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_signature': '%s&' % self.CONSUMER_SECRET,
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': 'requestnonce',
            'oauth_version': '1.0',
            'oauth_callback': 'http://printer.example.com/request_token_ready',
            'scope': 'photos', # custom argument to specify Protected Resource
        }

    def _make_access_token_parameters(self, token):
        return {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_token': token.key,
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_signature': '%s&%s' % (self.CONSUMER_SECRET, token.secret),
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': 'accessnonce',
            'oauth_version': '1.0',
            'oauth_verifier': token.verifier,
            'scope': 'photos',
        }

    def _make_protected_access_parameters(self, access_token):
        return {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_token': access_token.key,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': 'accessresourcenonce',
            'oauth_version': '1.0',
        }

    def test_returns_invalid_params_empty_request(self):
        """Printer website tries to access the photo and receives
        HTTP 401 Unauthorized indicating it is private.
        The Service Provider includes the following header with the response:
        """
        response = self.c.get("/oauth/request_token/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response._headers['www-authenticate'], ('WWW-Authenticate', 'OAuth realm=""'))
        self.assertEqual(response.content, 'Invalid request parameters.')

    def test_returns_401_wrong_callback(self):
        #If you try to put a wrong callback, it will return an error
        parameters = self._make_request_token_parameters()
        parameters['oauth_callback'] = 'wrongcallback'
        parameters['oauth_nonce'] = 'requestnoncewrongcallback'
        response = self.c.get("/oauth/request_token/", parameters)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.content, 'Invalid callback URL.')

    def test_401_for_wrong_scope(self):
        # If you try to access a resource with a wrong scope, it will return an error
        parameters = self._make_request_token_parameters()
        parameters['scope'] = 'videos'
        parameters['oauth_nonce'] = 'requestnoncevideos'

        response = self.c.get("/oauth/request_token/", parameters)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.content, 'Scope does not exist.')

    def test_oob_callback(self):
        # If you do not provide any callback (i.e. oob), the Service Provider SHOULD display the value of the verification code
        parameters = self._make_request_token_parameters()
        parameters['oauth_callback'] = 'oob'
        parameters['oauth_nonce'] = 'requestnonceoob'
        response = self.c.get("/oauth/request_token/", parameters)

        self.assertEqual(response.status_code, 200)
        response_params = cgi.parse_qs(response.content)
        oob_token = self._last_created_request_token()

        self.assertTrue(oob_token.key in response_params['oauth_token'])
        self.assertTrue(oob_token.secret in response_params['oauth_token_secret'])
        self.assertFalse(oob_token.callback_confirmed)
        self.assertIsNone(oob_token.callback)

    def _validate_request_token_response(self, response):
        self.assertEqual(response.status_code, 200)

        response_params = cgi.parse_qs(response.content)
        last_token = self._last_created_request_token()

        self.assertTrue(last_token.key in response_params['oauth_token'])
        self.assertTrue(last_token.secret in response_params['oauth_token_secret'])
        self.assertTrue(response_params['oauth_callback_confirmed'])

    def _obtain_request_token(self):
        parameters = self._make_request_token_parameters()
        response = self.c.get("/oauth/request_token/", parameters)

        # The Service Provider checks the signature and replies with an unauthorized Request Token in the body of the HTTP response
        self._validate_request_token_response(response)
        return self._last_created_request_token()

    def test_obtain_request_token(self):
        self._obtain_request_token()

    def test_provider_redirects_to_login_page(self):
        """The Service Provider asks Jane to sign-in using her username and password
        """
        token = self._obtain_request_token()
        parameters = {
            'oauth_token': token.key,
        }

        response = self.c.get("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(token.key in response['Location'])

        self.c.login(username='jane', password='toto')
        response = self.c.get("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 200)

    def test_authorize_without_session_parameter(self):
        # Then consumer obtains a Request Token
        token = self._obtain_request_token()
        parameters = {'oauth_token': token.key}

        self.c.login(username='jane', password='toto')

        parameters['authorize_access'] = True
        response = self.c.post("/oauth/authorize/", parameters)

        # without session parameter (previous POST removed it)
        response = self.c.post("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.content, 'Action not allowed.')

    def test_access_not_granted_by_the_user(self):
        token = self._obtain_request_token()
        parameters = {'oauth_token': token.key}

        self.c.login(username='jane', password='toto')

        self.c.get("/oauth/authorize/", parameters)  # set session id

        parameters['authorize_access'] = False
        response = self.c.post("/oauth/authorize/", parameters)
        self.assertTrue('error=Access+not+granted+by+user' in response['Location'])

    def _request_authorization(self, request_token):
        """Request authorization for the request token.
        """
        self.assertFalse(request_token.is_approved)

        parameters = {'oauth_token': request_token.key}
        self.c.login(username='jane', password='toto')
        response = self.c.get("/oauth/authorize/", parameters)
        parameters['authorize_access'] = 1
        self.c.post("/oauth/authorize/", parameters)

        request_token = self._update_token_from_db(request_token)
        self.assertTrue(request_token.is_approved)

    def test_request_authorization(self):
        token = self._obtain_request_token()
        self._request_authorization(token)

    def _obtain_access_token(self, request_token):
        parameters = self._make_access_token_parameters(request_token)

        response = self.c.get("/oauth/access_token/", parameters)
        response_params = cgi.parse_qs(response.content)

        access_token = self._last_created_access_token()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_params['oauth_token'][0], access_token.key)
        self.assertEqual(response_params['oauth_token_secret'][0], access_token.secret)
        self.assertEqual(access_token.user.username, 'jane')

        return access_token

    def test_request_another_access_token(self):
        """The Consumer will not be able to request another Access Token
        with the same parameters because the Request Token has been deleted
        once Access Token is created
        """
        request_token = self._obtain_request_token()
        self._request_authorization(request_token)
        request_token = self._update_token_from_db(request_token)
        self._obtain_access_token(request_token)

        parameters = self._make_access_token_parameters(request_token)
        response = self.c.get("/oauth/access_token/", parameters)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Invalid request token.')

    def test_request_access_token_invalid_verifier(self):
        """The Consumer will not be able to request another Access Token
        with a missing or invalid verifier
        """
        jane = User.objects.get(username='jane')
        new_request_token = Token.objects.create_token(
            token_type=Token.REQUEST,
            timestamp=str(int(time.time())),
            consumer=Consumer.objects.get(key=self.CONSUMER_KEY),
            user=jane,
            scope=Scope.objects.get(name='photos'))
        new_request_token.is_approved = True
        new_request_token.save()
        parameters = self._make_access_token_parameters(new_request_token)
        parameters['oauth_token'] = new_request_token.key
        parameters['oauth_signature'] = '%s&%s' % (self.CONSUMER_SECRET, new_request_token.secret)
        parameters['oauth_verifier'] = 'invalidverifier'
        response = self.c.get("/oauth/access_token/", parameters)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Invalid OAuth verifier.')

    def test_request_access_token_not_approved_request_token(self):
        """The Consumer will not be able to request an Access Token if the token is not approved
        """
        jane = User.objects.get(username='jane')
        new_request_token = Token.objects.create_token(
            token_type=Token.REQUEST,
            timestamp=str(int(time.time())),
            consumer=Consumer.objects.get(key=self.CONSUMER_KEY),
            user=jane,
            scope=Scope.objects.get(name='photos'))
        new_request_token.is_approved = False
        new_request_token.save()

        parameters = self._make_access_token_parameters(new_request_token)

        response = self.c.get("/oauth/access_token/", parameters)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Request Token not approved by the user.')

    def test_error_accessing_protected_resource(self):
        request_token = self._obtain_request_token()
        self._request_authorization(request_token)
        request_token = self._update_token_from_db(request_token)
        access_token = self._obtain_access_token(request_token)

        parameters = self._make_protected_access_parameters(access_token)

        parameters['oauth_signature'] = 'wrongsignature'
        parameters['oauth_nonce'] = 'anotheraccessresourcenonce'
        response = self.c.get("/oauth/photo/", parameters)

        self.assertEqual(response.status_code, 401)
        self.assertTrue(response.content.startswith('Could not verify OAuth request.'))

        response = self.c.get("/oauth/photo/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.content, 'Invalid request parameters.')

    def test_positive(self):
        # Then consumer obtains a Request Token
        parameters = self._make_request_token_parameters()
        response = self.c.get("/oauth/request_token/", parameters)

        # The Service Provider checks the signature and replies with an unauthorized Request Token in the body of the HTTP response
        self._validate_request_token_response(response)

        token = self._last_created_request_token()

        parameters = {'oauth_token': token.key}

        """The Consumer redirects Jane's browser to the Service Provider User Authorization URL
        to obtain Jane's approval for accessing her private photos.
        """

        response = self.c.get("/oauth/authorize/", parameters)

        """The Service Provider asks Jane to sign-in using her username and password
        """
        self.assertEqual(response.status_code, 302)
        expected_redirect = 'http://testserver/accounts/login/?next=/oauth/authorize/%3Foauth_token%3D{0}'.format(token.key)
        self.assertEqual(response['Location'], expected_redirect)

        # Jane logins
        self.c.login(username='jane', password='toto')

        """If successful, Service Provider asks her if she approves granting printer.example.com
        access to her private photos.
        """
        response = self.c.get("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(
            'Fake authorize view for printer.example.com with params: oauth_token='))

        # Jane approves the request.
        self.assertEqual(token.is_approved, 0)  # token is not approved yet

        parameters['authorize_access'] = 1
        response = self.c.post("/oauth/authorize/", parameters)

        # The Service Provider redirects her back to the Consumer's callback URL
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(
            'http://printer.example.com/request_token_ready?oauth_verifier='))
        self.assertTrue('oauth_token=' in response['Location'])

        token = self._last_created_request_token()  # get from the DB updated token
        self.assertTrue(token.is_approved)

        """
            Obtaining an Access Token
        """

        """Now that the Consumer knows Jane approved the Request Token,
        it asks the Service Provider to exchange it for an Access Token
        """

        # reset Client
        self.c = Client()
        parameters = self._make_access_token_parameters(token)

        response = self.c.get("/oauth/access_token/", parameters)

        """The Service Provider checks the signature and replies with an
        Access Token in the body of the HTTP response
        """
        self.assertEqual(response.status_code, 200)

        response_params = cgi.parse_qs(response.content)
        access_token = list(Token.objects.filter(token_type=Token.ACCESS))[-1]

        self.assertEqual(response_params['oauth_token'][0], access_token.key)
        self.assertEqual(response_params['oauth_token_secret'][0], access_token.secret)
        self.assertEqual(access_token.user.username, 'jane')

        """
            Accessing protected resources
        """

        """The Consumer is now ready to request the private photo.
        Since the photo URL is not secure (HTTP), it must use HMAC-SHA1.
        """

        """     Generating Signature Base String
        To generate the signature, it first needs to generate the Signature Base String.
        The request contains the following parameters (oauth_signature excluded)
        which are ordered and concatenated into a normalized string
        """
        parameters = self._make_protected_access_parameters(access_token)

        """ Calculating Signature Value
        HMAC-SHA1 produces the following digest value as a base64-encoded string
        (using the Signature Base String as text and self.CONSUMER_SECRET as key)
        """
        oauth_request = oauth.Request.from_token_and_callback(access_token,
            http_url='http://testserver/oauth/photo/',
            parameters=parameters)

        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, access_token)

        """ Requesting Protected Resource
        All together, the Consumer request for the photo is:
        """
        parameters['oauth_signature'] = signature
        response = self.c.get("/oauth/photo/", parameters)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'Protected Resource access!')

        """ Revoking Access
        If Jane deletes the Access Token of printer.example.com,
        the Consumer will not be able to access the Protected Resource anymore
        """
        access_token.delete()
        # Note that an "Invalid signature" error will be raised here if the
        # token is not revoked by Jane because we reuse a previously used one.
        parameters['oauth_signature'] = signature
        parameters['oauth_nonce'] = 'yetanotheraccessscopenonce'
        response = self.c.get(self.scope.url, parameters)
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response.content.startswith('Invalid access token:'))
