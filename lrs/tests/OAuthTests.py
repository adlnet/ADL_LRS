from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import views, models
from oauth_provider.oauth.oauth import OAuthRequest, OAuthSignatureMethod_HMAC_SHA1
from django.test.utils import setup_test_environment
from django.contrib.auth.models import User
import time
import pdb
from django.conf import settings

class OAuthTests(TestCase):
	def setUp(self):
		settings.OAUTH_ENABLED = True		
		# Create a user
		resource = models.Resource(name='statements', url='/TCAPI/statements/')
		resource.save()
		self.user = User.objects.create_user('jane', 'jane@example.com', 'toto')

		#Register a client
		self.name = "test client"
		self.desc = "test desc"
		form = {"name":self.name, "description":self.desc}
		response = self.client.post(reverse(views.reg_client),form, X_Experience_API_Version="0.95")
		self.consumer = models.Consumer.objects.get(name=self.name)

	def tearDown(self):
		# Delete everything
		models.Token.objects.all().delete()
		models.Consumer.objects.all().delete()
		models.Nonce.objects.all().delete()
		User.objects.all().delete()


	def test_simple(self):
		# Test request_token without appropriate headers
		resp = self.client.get("/TCAPI/OAuth/initiate/")
		self.assertEqual(resp.status_code, 401)
		self.assertIn('WWW-Authenticate', resp._headers['www-authenticate'])
		self.assertIn('OAuth realm="http://localhost:8000/TCAPI"', resp._headers['www-authenticate'])
		self.assertEqual(resp.content, 'Invalid request parameters.')

		# TEST REQUEST TOKEN
		oauth_header_request_params = {
			'oauth_consumer_key': self.consumer.key,
			'oauth_signature_method': 'PLAINTEXT',
			'oauth_signature':'%s&' % self.consumer.secret,
			'oauth_timestamp': str(int(time.time())),
			'oauth_nonce': 'requestnonce',
			'oauth_version': '1.0',
			'oauth_callback':'http://example.com/request_token_ready'
		}
		form_data = {
			'scope':'statements',
			'consumer_name': 'Example'
		}				
		request_resp = self.client.get("/TCAPI/OAuth/initiate/", Authorization=oauth_header_request_params, data=form_data)
		self.assertEqual(request_resp.status_code, 200)
		self.assertIn('oauth_token_secret=', request_resp.content)
		self.assertIn('oauth_token=', request_resp.content)
		self.assertIn('&oauth_callback_confirmed=true', request_resp.content)
		token = list(models.Token.objects.all())[-1]
		self.assertIn(token.key, request_resp.content)
		self.assertIn(token.secret, request_resp.content)
		self.assertEqual(token.callback, 'http://example.com/request_token_ready')
		self.assertEqual(token.callback_confirmed, True)

		# Test wrong scope
		form_data['scope'] = 'videos'
		scope_resp = self.client.get("/TCAPI/OAuth/initiate/", Authorization=oauth_header_request_params, data=form_data)
		self.assertEqual(scope_resp.status_code, 401)
		self.assertEqual(scope_resp.content, 'Resource videos does not exist.')
		form_data['scope'] = 'statements'

		# Test wrong callback
		oauth_header_request_params['oauth_callback'] = 'wrongcallback'
		call_resp = self.client.get("/TCAPI/OAuth/initiate/", Authorization=oauth_header_request_params, data=form_data)
		self.assertEqual(call_resp.status_code, 401)
		self.assertEqual(call_resp.content, 'Invalid callback URL.')

		# Test AUTHORIZE
		oauth_auth_params = {'oauth_token': token.key}
		auth_resp = self.client.get("/TCAPI/OAuth/authorize/", oauth_auth_params)
		self.assertEqual(auth_resp.status_code, 302)
		self.assertIn('http://testserver/accounts/login/?next=/TCAPI/OAuth/authorize/%3F', auth_resp['Location'])
		self.assertIn(token.key, auth_resp['Location'])
		self.client.login(username='jane', password='toto')
		self.assertEqual(token.is_approved, False)
		auth_resp = self.client.get("/TCAPI/OAuth/authorize/", oauth_auth_params)
		self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
		oauth_auth_params['authorize_access'] = 1
		auth_post = self.client.post("/TCAPI/OAuth/authorize/", oauth_auth_params)
		self.assertEqual(auth_post.status_code, 302)
		self.assertIn('http://example.com/request_token_ready?oauth_verifier=', auth_post['Location'])
		token = list(models.Token.objects.all())[-1]
		self.assertIn(token.key, auth_post['Location'])
		self.assertEqual(token.is_approved, True)

		# Test without session param (previous POST removed it)
		auth_post = self.client.post("/TCAPI/OAuth/authorize/", oauth_auth_params)
		self.assertEqual(auth_post.status_code, 401)
		self.assertEqual(auth_post.content, 'Action not allowed.')

		# Test fake access
		auth_resp = self.client.get("/TCAPI/OAuth/authorize/", oauth_auth_params)
		oauth_auth_params['authorize_access'] = 0
		auth_resp = self.client.post("/TCAPI/OAuth/authorize/", oauth_auth_params)
		self.assertEqual(auth_resp.status_code, 302)
		self.assertEqual(auth_resp['Location'], 'http://example.com/request_token_ready?error=Access%20not%20granted%20by%20user.')
		self.client.logout()

		# Test ACCESS TOKEN
		oauth_header_access_params = {
			'oauth_consumer_key': self.consumer.key,
			'oauth_token': token.key,
			'oauth_signature_method': 'PLAINTEXT',
			'oauth_signature':'%s&%s' % (self.consumer.secret, token.secret),
			'oauth_timestamp': str(int(time.time())),
			'oauth_nonce': 'accessnonce',
			'oauth_version': '1.0',
			'oauth_verifier': token.verifier
		}
		access_resp = self.client.get("/TCAPI/OAuth/token/", Authorization=oauth_header_access_params)
		self.assertEqual(access_resp.status_code, 200)
		access_token = list(models.Token.objects.filter(token_type=models.Token.ACCESS))[-1]
		self.assertIn(access_token.key, access_resp.content)
		self.assertEqual(access_token.user.username, u'jane')

		# Test same Nonce
		access_resp = self.client.get("/TCAPI/OAuth/token/", Authorization=oauth_header_access_params)
		self.assertEqual(access_resp.status_code, 401)
		self.assertEqual(access_resp.content, 'Nonce already used: accessnonce')

		# Test missing/invalid verifier
		oauth_header_access_params['oauth_nonce'] = 'yetanotheraccessnonce'
		oauth_header_access_params['oauth_verifier'] = 'invalidverifier'
		access_resp = self.client.get("/TCAPI/OAuth/token/", Authorization=oauth_header_access_params)
		self.assertEqual(access_resp.status_code, 401)
		self.assertEqual(access_resp.content, 'Consumer key or token key does not match. Make sure your request token is approved. Check your verifier too if you use OAuth 1.0a.')    	
		oauth_header_access_params['oauth_verifier'] = token.verifier

		# Test token not approved
		oauth_header_access_params['oauth_nonce'] = 'anotheraccessnonce'
		token.is_approved = False
		token.save()
		access_resp = self.client.get("/TCAPI/OAuth/token/", Authorization=oauth_header_access_params)
		self.assertEqual(access_resp.status_code, 401)
		self.assertEqual(access_resp.content, 'Consumer key or token key does not match. Make sure your request token is approved. Check your verifier too if you use OAuth 1.0a.')

		# Test ACCESS RESOURCE
		oauth_header_resource_params = {
			'oauth_consumer_key': self.consumer.key,
			'oauth_token': access_token.key,
			'oauth_signature_method': 'HMAC-SHA1',
			'oauth_timestamp': str(int(time.time())),
			'oauth_nonce': 'accessresourcenonce',
			'oauth_version': '1.0'
		}
		oauth_request = OAuthRequest.from_token_and_callback(access_token,
			http_url='http://testserver/TCAPI/statements/', parameters=oauth_header_resource_params)
		signature_method = OAuthSignatureMethod_HMAC_SHA1()
		signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
		oauth_header_resource_params['oauth_signature'] = signature
		resp = self.client.get("/TCAPI/statements/", Authorization=oauth_header_resource_params)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.content, '{"statements": [], "more": ""}')

		# Test wrong signature
		oauth_header_resource_params['oauth_signature'] = 'wrongsignature'
		oauth_header_resource_params['oauth_nonce'] = 'anotheraccessresourcenonce'
		resp = self.client.get("/TCAPI/statements/", Authorization=oauth_header_resource_params)
		self.assertEqual(resp.status_code, 401)
		self.assertIn('Invalid signature.', resp.content)

		# Test wrong params - will not return 'Invalid request parameters.' like oauth example states
		# because there is no Authorization header. With no auth header the lrs reads as no auth supplied at all
		pdb.set_trace()
		resp = self.client.get("/TCAPI/statements/")
		self.assertEqual(resp.status_code, 401)
		self.assertEqual(resp.content, 'Auth is enabled but no authentication was sent with the request.')

		# Test revoke access
		access_token.delete()
		oauth_header_resource_params['oauth_signature'] = signature
		oauth_header_resource_params['oauth_nonce'] = 'yetanotheraccessresourcenonce'
		resp = self.client.get("/TCAPI/statements/", Authorization=oauth_header_resource_params)
		self.assertEqual(resp.status_code, 401)
		self.assertIn('Invalid access token', resp.content)

	def test_oauth_disabled(self):
		settings.OAUTH_ENABLED = False
		# Test request_token without appropriate headers

		# TEST REQUEST TOKEN
		oauth_header_request_params = {
			'oauth_consumer_key': self.consumer.key,
			'oauth_signature_method': 'PLAINTEXT',
			'oauth_signature':'%s&' % self.consumer.secret,
			'oauth_timestamp': str(int(time.time())),
			'oauth_nonce': 'requestnonce',
			'oauth_version': '1.0',
			'oauth_callback':'http://example.com/request_token_ready'
		}
		form_data = {
			'scope':'statements',
			'consumer_name': 'Example'
		}				
		request_resp = self.client.get("/TCAPI/OAuth/initiate/", Authorization=oauth_header_request_params, data=form_data)
		self.assertEqual(request_resp.status_code, 200)
		self.assertIn('oauth_token_secret=', request_resp.content)
		self.assertIn('oauth_token=', request_resp.content)
		self.assertIn('&oauth_callback_confirmed=true', request_resp.content)
		token = list(models.Token.objects.all())[-1]
		self.assertIn(token.key, request_resp.content)
		self.assertIn(token.secret, request_resp.content)
		self.assertEqual(token.callback, 'http://example.com/request_token_ready')
		self.assertEqual(token.callback_confirmed, True)

		# Test AUTHORIZE
		oauth_auth_params = {'oauth_token': token.key}
		auth_resp = self.client.get("/TCAPI/OAuth/authorize/", oauth_auth_params)
		self.assertEqual(auth_resp.status_code, 302)
		self.assertIn('http://testserver/accounts/login/?next=/TCAPI/OAuth/authorize/%3F', auth_resp['Location'])
		self.assertIn(token.key, auth_resp['Location'])
		self.client.login(username='jane', password='toto')
		self.assertEqual(token.is_approved, False)
		auth_resp = self.client.get("/TCAPI/OAuth/authorize/", oauth_auth_params)
		self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
		oauth_auth_params['authorize_access'] = 1
		auth_post = self.client.post("/TCAPI/OAuth/authorize/", oauth_auth_params)
		self.assertEqual(auth_post.status_code, 302)
		self.assertIn('http://example.com/request_token_ready?oauth_verifier=', auth_post['Location'])
		token = list(models.Token.objects.all())[-1]
		self.assertIn(token.key, auth_post['Location'])
		self.assertEqual(token.is_approved, True)

		# Test ACCESS TOKEN
		oauth_header_access_params = {
			'oauth_consumer_key': self.consumer.key,
			'oauth_token': token.key,
			'oauth_signature_method': 'PLAINTEXT',
			'oauth_signature':'%s&%s' % (self.consumer.secret, token.secret),
			'oauth_timestamp': str(int(time.time())),
			'oauth_nonce': 'accessnonce',
			'oauth_version': '1.0',
			'oauth_verifier': token.verifier
		}
		access_resp = self.client.get("/TCAPI/OAuth/token/", Authorization=oauth_header_access_params)
		self.assertEqual(access_resp.status_code, 200)
		access_token = list(models.Token.objects.filter(token_type=models.Token.ACCESS))[-1]
		self.assertIn(access_token.key, access_resp.content)
		self.assertEqual(access_token.user.username, u'jane')

		# Test ACCESS RESOURCE
		oauth_header_resource_params = {
			'oauth_consumer_key': self.consumer.key,
			'oauth_token': access_token.key,
			'oauth_signature_method': 'HMAC-SHA1',
			'oauth_timestamp': str(int(time.time())),
			'oauth_nonce': 'accessresourcenonce',
			'oauth_version': '1.0'
		}
		oauth_request = OAuthRequest.from_token_and_callback(access_token,
			http_url='http://testserver/TCAPI/statements/', parameters=oauth_header_resource_params)
		signature_method = OAuthSignatureMethod_HMAC_SHA1()
		signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
		oauth_header_resource_params['oauth_signature'] = signature
		resp = self.client.get("/TCAPI/statements/", Authorization=oauth_header_resource_params)
		self.assertEqual(resp.status_code, 400)
		self.assertEqual(resp.content, 'OAuth is not enabled. To enable, set the OAUTH_ENABLED flag to true in settings')


