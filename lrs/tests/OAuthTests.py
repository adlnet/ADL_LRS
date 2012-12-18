from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import views, models
from oauth_provider.oauth.oauth import OAuthRequest, OAuthSignatureMethod_HMAC_SHA1
from django.test.utils import setup_test_environment
from django.contrib.auth.models import User
from lrs.objects import Statement
import time
import pdb
from django.conf import settings
import uuid
import json
import urllib
from BeautifulSoup import BeautifulSoup

class OAuthTests(TestCase):
	def setUp(self):
		settings.OAUTH_ENABLED = True

		# Create the all resource
		all_resource = models.Resource(name='all', url='*')
		all_resource.save()
		# Create a user		
		self.user = User.objects.create_user('jane', 'jane@example.com', 'toto')

		#Register a client
		self.name = "test client"
		self.desc = "test desc"
		form = {"name":self.name, "description":self.desc}
		response = self.client.post(reverse(views.reg_client),form, X_Experience_API_Version="0.95")
		self.consumer = models.Consumer.objects.get(name=self.name)

	def perform_oauth_handshake(self):
		settings.OAUTH_ENABLED = True		

		# TEST REQUEST TOKEN
		oauth_header_request_params = {
			'oauth_consumer_key': self.consumer.key,
			'oauth_signature_method': 'PLAINTEXT',
			'oauth_signature':'%s&' % self.consumer.secret,
			'oauth_timestamp': str(int(time.time())),
			'oauth_nonce': 'requestnonce',
			'oauth_version': '1.0',
			'oauth_callback':'oob'
		}
		# Test sending in scope as query param with REQUEST_TOKEN
		param = {
					"scope":"all"
				}
		path = "%s?%s" % ("/TCAPI/OAuth/initiate", urllib.urlencode(param))					
		request_resp = self.client.get(path, Authorization=oauth_header_request_params, X_Experience_API_Version="0.95")		
		self.assertEqual(request_resp.status_code, 200)
		self.assertIn('oauth_token_secret=', request_resp.content)
		self.assertIn('oauth_token=', request_resp.content)
		# self.assertIn('&oauth_callback_confirmed=true', request_resp.content)
		token = list(models.Token.objects.all())[-1]
		self.assertIn(token.key, request_resp.content)
		self.assertIn(token.secret, request_resp.content)
		self.assertEqual(token.callback, None)
		self.assertEqual(token.callback_confirmed, False)

		# Test AUTHORIZE
		oauth_auth_params = {'oauth_token': token.key}
		auth_resp = self.client.get("/TCAPI/OAuth/authorize", oauth_auth_params, X_Experience_API_Version="0.95")
		self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
		oauth_auth_params['authorize_access'] = 1
		# Parse out auth_id and set in oauth_auth_params
		soup = BeautifulSoup(auth_resp.content)
		p = soup.findAll('p')
		oauth_auth_params['lrs_auth_id'] = str(p[1].contents[0])
		pdb.set_trace()
		auth_post = self.client.post("/TCAPI/OAuth/authorize", oauth_auth_params, X_Experience_API_Version="0.95")
		self.assertEqual(auth_post.status_code, 200)
		self.assertEqual(auth_post.content, "Callback view. - You've been authenticated!")


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
		access_resp = self.client.get("/TCAPI/OAuth/token/", Authorization=oauth_header_access_params,
			X_Experience_API_Version="0.95")
		self.assertEqual(access_resp.status_code, 200)
		access_token = list(models.Token.objects.filter(token_type=models.Token.ACCESS))[-1]
		self.assertIn(access_token.key, access_resp.content)
		self.assertEqual(access_token.lrs_auth_id, str(p[1].contents[0]))

		# Test ACCESS RESOURCE
		oauth_header_resource_params = {
			'oauth_consumer_key': self.consumer.key,
			'oauth_token': access_token.key,
			'oauth_signature_method': 'HMAC-SHA1',
			'oauth_timestamp': str(int(time.time())),
			'oauth_nonce': 'accessresourcenonce',
			'oauth_version': '1.0'
		}

		return oauth_header_resource_params, access_token

	def tearDown(self):
		# Delete everything
		models.Token.objects.all().delete()
		models.Consumer.objects.all().delete()
		models.Nonce.objects.all().delete()
		User.objects.all().delete()


	def test_all_error_flows(self):
		# Test request_token without appropriate headers
		resp = self.client.get("/TCAPI/OAuth/initiate",  X_Experience_API_Version="0.95")
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
			'oauth_callback': 'oob'
		}
		# Test sending scope in as form param with REQUEST_TOKEN
		form_data = {
			'scope':'all',
		}			
		request_resp = self.client.get("/TCAPI/OAuth/initiate", Authorization=oauth_header_request_params, data=form_data,
		 X_Experience_API_Version="0.95")
		self.assertEqual(request_resp.status_code, 200)
		self.assertIn('oauth_token_secret=', request_resp.content)
		self.assertIn('oauth_token=', request_resp.content)
		token = list(models.Token.objects.all())[-1]
		self.assertIn(token.key, request_resp.content)
		self.assertIn(token.secret, request_resp.content)

		# Test wrong scope
		form_data['scope'] = 'videos'
		scope_resp = self.client.get("/TCAPI/OAuth/initiate", Authorization=oauth_header_request_params, data=form_data,
			 X_Experience_API_Version="0.95")
		self.assertEqual(scope_resp.status_code, 401)
		self.assertEqual(scope_resp.content, 'Resource videos does not exist.')
		form_data['scope'] = 'statements'

		# Test wrong callback
		oauth_header_request_params['oauth_callback'] = 'wrongcallback'
		call_resp = self.client.get("/TCAPI/OAuth/initiate", Authorization=oauth_header_request_params, data=form_data,
			 X_Experience_API_Version="0.95")
		self.assertEqual(call_resp.status_code, 401)
		self.assertEqual(call_resp.content, 'Invalid callback URL.')

		# Test AUTHORIZE
		oauth_auth_params = {'oauth_token': token.key}
		auth_resp = self.client.get("/TCAPI/OAuth/authorize", oauth_auth_params, X_Experience_API_Version="0.95")
		self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
		oauth_auth_params['authorize_access'] = 1

		# Parse out auth_id and set in oauth_auth_params
		soup = BeautifulSoup(auth_resp.content)
		p = soup.findAll('p')
		oauth_auth_params['lrs_auth_id'] = str(p[1].contents[0])
		auth_post = self.client.post("/TCAPI/OAuth/authorize", oauth_auth_params, X_Experience_API_Version="0.95")
		self.assertEqual(auth_post.status_code, 200)
		self.assertEqual(auth_post.content, "Callback view. - You've been authenticated!")

		# Test without session param (previous POST removed it)
		auth_post = self.client.post("/TCAPI/OAuth/authorize", oauth_auth_params, X_Experience_API_Version="0.95")
		self.assertEqual(auth_post.status_code, 401)
		self.assertEqual(auth_post.content, 'Action not allowed.')

		# Test fake access
		auth_resp = self.client.get("/TCAPI/OAuth/authorize", oauth_auth_params, X_Experience_API_Version="0.95")
		oauth_auth_params['authorize_access'] = 0
		auth_resp = self.client.post("/TCAPI/OAuth/authorize", oauth_auth_params, X_Experience_API_Version="0.95")
		self.assertEqual(auth_resp.status_code, 200)
		self.assertEqual(auth_resp.content, 'Error - Access not granted by user.')

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
		access_resp = self.client.get("/TCAPI/OAuth/token/", Authorization=oauth_header_access_params,
			X_Experience_API_Version="0.95")
		self.assertEqual(access_resp.status_code, 200)
		access_token = list(models.Token.objects.filter(token_type=models.Token.ACCESS))[-1]
		self.assertIn(access_token.key, access_resp.content)
		# self.assertEqual(access_token.user.username, u'jane')
		self.assertEqual(access_token.lrs_auth_id, str(p[1].contents[0]))

		# Test same Nonce
		access_resp = self.client.get("/TCAPI/OAuth/token/", Authorization=oauth_header_access_params,
			 X_Experience_API_Version="0.95")
		self.assertEqual(access_resp.status_code, 401)
		self.assertEqual(access_resp.content, 'Nonce already used: accessnonce')

		# Test missing/invalid verifier - doesn't get validated since there is oob callback
		# oauth_header_access_params['oauth_nonce'] = 'yetanotheraccessnonce'
		# oauth_header_access_params['oauth_verifier'] = 'invalidverifier'
		# pdb.set_trace()
		# access_resp = self.client.get("/TCAPI/OAuth/token/", Authorization=oauth_header_access_params,
		# 	X_Experience_API_Version="0.95")
		# pdb.set_trace()
		# self.assertEqual(access_resp.status_code, 401)
		# self.assertEqual(access_resp.content, 'Consumer key or token key does not match. Make sure your request token is approved. Check your verifier too if you use OAuth 1.0a.')    	
		# oauth_header_access_params['oauth_verifier'] = token.verifier

		# Test token not approved
		oauth_header_access_params['oauth_nonce'] = 'anotheraccessnonce'
		token.is_approved = False
		token.save()
		access_resp = self.client.get("/TCAPI/OAuth/token/", Authorization=oauth_header_access_params,
			 X_Experience_API_Version="0.95")
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
		resp = self.client.get("/TCAPI/statements/", Authorization=oauth_header_resource_params,
			X_Experience_API_Version="0.95")
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.content, '{"statements": [], "more": ""}')

		# Test wrong signature
		oauth_header_resource_params['oauth_signature'] = 'wrongsignature'
		oauth_header_resource_params['oauth_nonce'] = 'anotheraccessresourcenonce'
		resp = self.client.get("/TCAPI/statements/", Authorization=oauth_header_resource_params,
			X_Experience_API_Version="0.95")
		self.assertEqual(resp.status_code, 401)
		self.assertIn('Invalid signature.', resp.content)

		# Test wrong params - will not return 'Invalid request parameters.' like oauth example states
		# because there is no Authorization header. With no auth header the lrs reads as no auth supplied at all
		resp = self.client.get("/TCAPI/statements/", X_Experience_API_Version="0.95")
		self.assertEqual(resp.status_code, 401)
		self.assertEqual(resp.content, 'Auth is enabled but no authentication was sent with the request.')

		# Test revoke access
		access_token.delete()
		oauth_header_resource_params['oauth_signature'] = signature
		oauth_header_resource_params['oauth_nonce'] = 'yetanotheraccessresourcenonce'
		resp = self.client.get("/TCAPI/statements/", Authorization=oauth_header_resource_params,
			X_Experience_API_Version="0.95")
		self.assertEqual(resp.status_code, 401)
		self.assertIn('Invalid access token', resp.content)

	def test_oauth_disabled(self):
		# Disable oauth
		settings.OAUTH_ENABLED = False

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
		# Test sending in scope as query param with REQUEST_TOKEN
		param = {
					"scope":"all"
				}
		path = "%s?%s" % ("/TCAPI/OAuth/initiate", urllib.urlencode(param))					
		request_resp = self.client.get(path, Authorization=oauth_header_request_params, X_Experience_API_Version="0.95")		
		self.assertEqual(request_resp.status_code, 400)
		self.assertEqual(request_resp.content,'OAuth is not enabled. To enable, set the OAUTH_ENABLED flag to true in settings' )

	def test_stmt_put(self):
		put_guid = str(uuid.uuid4())
		stmt = json.dumps({"actor":{"objectType": "Agent", "mbox":"t@t.com", "name":"bill"},
			"verb":{"id": "http://adlnet.gov/expapi/verbs/accessed","display": {"en-US":"accessed"}},
			"object": {"id":"test_put"}})
		param = {"statementId":put_guid}
		path = "%s?%s" % ('http://testserver/TCAPI/statements', urllib.urlencode(param))
		
		oauth_header_resource_params, access_token = self.perform_oauth_handshake()
		
		oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='PUT',
			http_url=path, parameters=oauth_header_resource_params)
		signature_method = OAuthSignatureMethod_HMAC_SHA1()
		signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
		oauth_header_resource_params['oauth_signature'] = signature
		
		# Put statements
		resp = self.client.put(path, data=stmt, content_type="application/json",
			Authorization=oauth_header_resource_params, X_Experience_API_Version="0.95")
		self.assertEqual(resp.status_code, 204)

	def test_stmt_post_no_scope(self):
		stmt = json.dumps({"actor":{"objectType": "Agent", "mbox":"t@t.com", "name":"bob"},
			"verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
			"object": {"id":"test_post"}})

		oauth_header_resource_params, access_token = self.perform_oauth_handshake()

		oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='POST',
			http_url='http://testserver/TCAPI/statements/', parameters=oauth_header_resource_params)
		signature_method = OAuthSignatureMethod_HMAC_SHA1()
		signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
		oauth_header_resource_params['oauth_signature'] = signature
		
		resp = self.client.post('/TCAPI/statements/', data=stmt, content_type="application/json",
			Authorization=oauth_header_resource_params, X_Experience_API_Version="0.95")
		self.assertEqual(resp.status_code, 200)

	def test_stmt_simple_get(self):
		guid = str(uuid.uuid4())
		stmt = Statement.Statement(json.dumps({"statement_id":guid,"actor":{"objectType": "Agent", "mbox":"t@t.com", "name":"bob"},
			"verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
			"object": {"id":"test_simple_get"}}))
		param = {"statementId":guid}
		path = "%s?%s" % ('http://testserver/TCAPI/statements', urllib.urlencode(param))

		oauth_header_resource_params, access_token = self.perform_oauth_handshake()

		oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
			http_url=path, parameters=oauth_header_resource_params)
		signature_method = OAuthSignatureMethod_HMAC_SHA1()
		signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
		oauth_header_resource_params['oauth_signature'] = signature

		resp = self.client.get(path,Authorization=oauth_header_resource_params, X_Experience_API_Version="0.95")
		self.assertEqual(resp.status_code, 200)
		rsp = resp.content
		self.assertIn(guid, rsp)

	def test_stmt_complex_get(self):
		stmt = Statement.Statement(json.dumps({"actor":{"objectType": "Agent", "mbox":"t@t.com", "name":"bob"},
			"verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
			"object": {"id":"test_complex_get"}}))
		param = {"object":{"objectType": "Activity", "id":"test_complex_get"}}
		path = "%s?%s" % ('http://testserver/TCAPI/statements', urllib.urlencode(param))

		oauth_header_resource_params, access_token = self.perform_oauth_handshake()

		oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
			http_url=path, parameters=oauth_header_resource_params)
		signature_method = OAuthSignatureMethod_HMAC_SHA1()
		signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
		oauth_header_resource_params['oauth_signature'] = signature

		resp = self.client.get(path,Authorization=oauth_header_resource_params, X_Experience_API_Version="0.95")		
		self.assertEqual(resp.status_code, 200)