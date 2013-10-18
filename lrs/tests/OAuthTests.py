from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import views, models
from oauth_provider.oauth.oauth import OAuthRequest, OAuthSignatureMethod_HMAC_SHA1
from django.test.utils import setup_test_environment
from django.contrib.auth.models import User
from lrs.objects.StatementManager import StatementManager
import time
from django.conf import settings
import uuid
import json
import urllib
import ast
import os
import hashlib
import base64
import re

class OAuthTests(TestCase):
    @classmethod
    def setUpClass(cls):
        print "\n%s" % __name__

    def setUp(self):
        if not settings.OAUTH_ENABLED:
            settings.OAUTH_ENABLED = True

        # Create a user
        self.user = User.objects.create_user('jane', 'jane@example.com', 'toto')
        user = self.client.login(username='jane', password='toto')

        #Register a client
        self.name = "test client"
        self.desc = "test desc"
        form = {"name":self.name, "description":self.desc, "scopes":"all"}
        response = self.client.post(reverse(views.reg_client),form, X_Experience_API_Version="1.0.0")
        self.consumer = models.Consumer.objects.get(name=self.name)
        self.client.logout()

        # Create a user
        self.user2 = User.objects.create_user('dick', 'dick@example.com', 'lassie')
        user2 = self.client.login(username='dick', password='lassie')

        #Register a client
        self.name2 = "test client2"
        self.desc2 = "test desc2"
        form2 = {"name":self.name2, "description":self.desc2, "scopes":"all"}
        response2 = self.client.post(reverse(views.reg_client),form2, X_Experience_API_Version="1.0.0")
        self.consumer2 = models.Consumer.objects.get(name=self.name2)
        self.client.logout()
    
    
    def perform_oauth_handshake(self, scope=True, scope_type=None, request_nonce=None,
        access_nonce=None, resource_nonce=None):
        # TEST REQUEST TOKEN
        oauth_header_request_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_signature=\"%s&\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,self.consumer.secret,str(int(time.time())))
        
        if scope:
            if scope_type:
                # Test sending in scope as query param with REQUEST_TOKEN
                param = {
                            "scope":scope_type
                        }
            else:
                # Test sending in scope as query param with REQUEST_TOKEN
                param = {
                            "scope":"all"
                        }
            path = "%s?%s" % ("/XAPI/OAuth/initiate", urllib.urlencode(param))                  
        else:
            path = "/XAPI/OAuth/initiate"

        request_resp = self.client.get(path, Authorization=oauth_header_request_params, X_Experience_API_Version="1.0.0")        

        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret=', request_resp.content)
        self.assertIn('oauth_token=', request_resp.content)
        self.assertIn('&oauth_callback_confirmed=true', request_resp.content)
        token = models.Token.objects.get(consumer=self.consumer)
        self.assertIn(token.key, request_resp.content)
        self.assertIn(token.secret, request_resp.content)
        self.assertEqual(token.callback, 'http://example.com/request_token_ready')
        self.assertEqual(token.callback_confirmed, True)

        # Test AUTHORIZE
        oauth_auth_params = {'oauth_token': token.key}
        auth_resp = self.client.get("/XAPI/OAuth/authorize", oauth_auth_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn('http://testserver/XAPI/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])    
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        auth_resp = self.client.get("/XAPI/OAuth/authorize/", oauth_auth_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
        
        html = auth_resp.content
        cap = re.search('name="obj_id"\Wvalue="(.*?)"', html)
        oauth_auth_params['obj_id'] = cap.group(1)

        caps = re.findall('checked="checked".*?value="(.*?)"', html)
        oauth_auth_params['scopes'] = [c for c in caps]

        oauth_auth_params['authorize_access'] = 1
        auth_post = self.client.post("/XAPI/OAuth/authorize/", oauth_auth_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_post.status_code, 302)
        self.assertIn('http://example.com/request_token_ready?oauth_verifier=', auth_post['Location'])
        token = models.Token.objects.get(consumer=self.consumer)
        self.assertIn(token.key, auth_post['Location'])
        self.assertEqual(token.is_approved, True)


        # Test ACCESS TOKEN
        oauth_header_access_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_signature=\"%s&%s\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"accessnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_verifier=\"%s\"" % (self.consumer.key,token.key,self.consumer.secret,token.secret,str(int(time.time())),token.verifier)

        access_resp = self.client.get("/XAPI/OAuth/token/", Authorization=oauth_header_access_params,
            X_Experience_API_Version="1.0.0")

        self.assertEqual(access_resp.status_code, 200)
        access_token = models.Token.objects.filter(token_type=models.Token.ACCESS, consumer=self.consumer)[0]
        self.assertIn(access_token.key, access_resp.content)
        self.assertEqual(access_token.user.username, u'jane')

        # Test ACCESS RESOURCE
        oauth_header_resource_params = "OAuth realm=\"test\", "\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"accessresourcenonce\","\
            "oauth_version=\"1.0\"" % (self.consumer.key, access_token.key, str(int(time.time())))

        return oauth_header_resource_params, access_token

    def perform_oauth_handshake2(self, scope=True, scope_type=None, request_nonce=None,
        access_nonce=None, resource_nonce=None):
        # TEST REQUEST TOKEN
        oauth_header_request_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_signature=\"%s&\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonc2e\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example2.com/request_token_ready\"" % (self.consumer2.key,self.consumer2.secret,str(int(time.time())))
        
        if scope:
            if scope_type:
                # Test sending in scope as query param with REQUEST_TOKEN
                param = {
                            "scope":scope_type
                        }
            else:
                # Test sending in scope as query param with REQUEST_TOKEN
                param = {
                            "scope":"all"
                        }
            path = "%s?%s" % ("/XAPI/OAuth/initiate", urllib.urlencode(param))                  
        else:
            path = "/XAPI/OAuth/initiate"

        request_resp = self.client.get(path, Authorization=oauth_header_request_params, X_Experience_API_Version="1.0.0")        

        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret=', request_resp.content)
        self.assertIn('oauth_token=', request_resp.content)
        self.assertIn('&oauth_callback_confirmed=true', request_resp.content)
        token = models.Token.objects.get(consumer=self.consumer2)
        self.assertIn(token.key, request_resp.content)
        self.assertIn(token.secret, request_resp.content)
        self.assertEqual(token.callback, 'http://example2.com/request_token_ready')
        self.assertEqual(token.callback_confirmed, True)

        # Test AUTHORIZE
        oauth_auth_params = {'oauth_token': token.key}
        auth_resp = self.client.get("/XAPI/OAuth/authorize", oauth_auth_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn('http://testserver/XAPI/accounts/login?next=/XAPI/OAuth/authorize%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])    
        self.client.login(username='dick', password='lassie')
        self.assertEqual(token.is_approved, False)
        auth_resp = self.client.get("/XAPI/OAuth/authorize/", oauth_auth_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
        
        html = auth_resp.content
        cap = re.search('name="obj_id"\Wvalue="(.*?)"', html)
        oauth_auth_params['obj_id'] = cap.group(1)

        caps = re.findall('checked="checked".*?value="(.*?)"', html)
        oauth_auth_params['scopes'] = [c for c in caps]

        oauth_auth_params['authorize_access'] = 1
        auth_post = self.client.post("/XAPI/OAuth/authorize/", oauth_auth_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_post.status_code, 302)
        self.assertIn('http://example2.com/request_token_ready?oauth_verifier=', auth_post['Location'])
        token = models.Token.objects.get(consumer=self.consumer2)
        self.assertIn(token.key, auth_post['Location'])
        self.assertEqual(token.is_approved, True)


        # Test ACCESS TOKEN
        oauth_header_access_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_signature=\"%s&%s\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"accessnonce2\","\
            "oauth_version=\"1.0\","\
            "oauth_verifier=\"%s\"" % (self.consumer2.key,token.key,self.consumer2.secret,token.secret,str(int(time.time())),token.verifier)

        access_resp = self.client.get("/XAPI/OAuth/token/", Authorization=oauth_header_access_params,
            X_Experience_API_Version="1.0.0")

        self.assertEqual(access_resp.status_code, 200)
        access_token = models.Token.objects.filter(token_type=models.Token.ACCESS, consumer=self.consumer2)[0]
        self.assertIn(access_token.key, access_resp.content)
        self.assertEqual(access_token.user.username, u'dick')

        # Test ACCESS RESOURCE
        oauth_header_resource_params = "OAuth realm=\"test\", "\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"HMAC-SHA1\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"accessresourcenonce2\","\
            "oauth_version=\"1.0\"" % (self.consumer2.key, access_token.key, str(int(time.time())))

        return oauth_header_resource_params, access_token



    def tearDown(self):
        if settings.OAUTH_ENABLED:
            settings.OAUTH_ENABLED = False
        # Delete everything
        models.Token.objects.all().delete()
        models.Consumer.objects.all().delete()
        models.Nonce.objects.all().delete()
        User.objects.all().delete()

        attach_folder_path = os.path.join(settings.MEDIA_ROOT, "activity_state")
        for the_file in os.listdir(attach_folder_path):
            file_path = os.path.join(attach_folder_path, the_file)
            try:
                os.unlink(file_path)
            except Exception, e:
                raise e

    def test_all_error_flows(self):
        # Test request_token without appropriate headers
        resp = self.client.get("/XAPI/OAuth/initiate/", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 401)
        self.assertIn('WWW-Authenticate', resp._headers['www-authenticate'])
        self.assertIn('OAuth realm="http://localhost:8000/XAPI"', resp._headers['www-authenticate'])
        self.assertEqual(resp.content, 'Invalid request parameters.')

        oauth_header_request_params = "OAuth realm=\"test\","\
               "oauth_consumer_key=\"%s\","\
               "oauth_signature_method=\"PLAINTEXT\","\
               "oauth_signature=\"%s&\","\
               "oauth_timestamp=\"%s\","\
               "oauth_nonce=\"requestnonce\","\
               "oauth_version=\"1.0\","\
               "oauth_callback=\"http://example.com/request_token_ready\"" % (self.consumer.key,self.consumer.secret,str(int(time.time())))

        # Test passing scope as form param
        form_data = {
            'scope':'all',
        }               
        request_resp = self.client.get("/XAPI/OAuth/initiate/", Authorization=oauth_header_request_params, data=form_data, X_Experience_API_Version="1.0.0")
        self.assertEqual(request_resp.status_code, 200)
        self.assertIn('oauth_token_secret=', request_resp.content)
        self.assertIn('oauth_token=', request_resp.content)
        self.assertIn('&oauth_callback_confirmed=true', request_resp.content)
        token = models.Token.objects.get(consumer=self.consumer)
        self.assertIn(token.key, request_resp.content)
        self.assertIn(token.secret, request_resp.content)
        self.assertEqual(token.callback, 'http://example.com/request_token_ready')
        self.assertEqual(token.callback_confirmed, True)

        # Test wrong scope
        form_data['scope'] = 'videos'
        scope_resp = self.client.get("/XAPI/OAuth/initiate/", Authorization=oauth_header_request_params, data=form_data, X_Experience_API_Version="1.0.0")
        self.assertEqual(scope_resp.status_code, 401)
        self.assertEqual(scope_resp.content, 'Resource videos is not allowed.')
        form_data['scope'] = 'all'

        # Test wrong callback
        oauth_header_request_params += ',oauth_callback="wrongcallback"'
        call_resp = self.client.get("/XAPI/OAuth/initiate/", Authorization=oauth_header_request_params, data=form_data, X_Experience_API_Version="1.0.0")
        self.assertEqual(call_resp.status_code, 401)
        self.assertEqual(call_resp.content, 'Invalid callback URL.')

        # Test AUTHORIZE
        oauth_auth_params = {'oauth_token': token.key}
        auth_resp = self.client.get("/XAPI/OAuth/authorize/", oauth_auth_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn('http://testserver/XAPI/accounts/login?next=/XAPI/OAuth/authorize/%3F', auth_resp['Location'])
        self.assertIn(token.key, auth_resp['Location'])
        self.client.login(username='jane', password='toto')
        self.assertEqual(token.is_approved, False)
        auth_resp = self.client.get("/XAPI/OAuth/authorize/", oauth_auth_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 200) # Show return/display OAuth authorized view
        html = auth_resp.content
        # <input type="hidden" name="obj_id" value="38" id="id_obj_id">
        # hidden.*name="obj_id"\Wvalue="(.*?)"
        cap = re.search('name="obj_id"\Wvalue="(.*?)"', html)
        oauth_auth_params['obj_id'] = cap.group(1)

        # <input checked="checked" type="checkbox" name="scopes" value="statements/write">
        # input\Wchecked="checked".*?value="(.*?)"
        caps = re.findall('checked="checked".*?value="(.*?)"', html)
        oauth_auth_params['scopes'] = [c for c in caps]

        oauth_auth_params['authorize_access'] = 1

        oauth_auth_params['authorize_access'] = 1
        auth_post = self.client.post("/XAPI/OAuth/authorize/", oauth_auth_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_post.status_code, 302)
        self.assertIn('http://example.com/request_token_ready?oauth_verifier=', auth_post['Location'])
        token = models.Token.objects.get(consumer=self.consumer)
        self.assertIn(token.key, auth_post['Location'])
        self.assertEqual(token.is_approved, True)

        # Test without session param (previous POST removed it)
        auth_post = self.client.post("/XAPI/OAuth/authorize/", oauth_auth_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_post.status_code, 401)
        self.assertEqual(auth_post.content, 'Action not allowed.')

        # Test fake access
        auth_resp = self.client.get("/XAPI/OAuth/authorize/", oauth_auth_params, X_Experience_API_Version="1.0.0")
        oauth_auth_params['authorize_access'] = 0
        auth_resp = self.client.post("/XAPI/OAuth/authorize/", oauth_auth_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(auth_resp.status_code, 302)
        self.assertEqual(auth_resp['Location'], 'http://example.com/request_token_ready?error=Access%20not%20granted%20by%20user.')
        self.client.logout()

        # Test ACCESS TOKEN
        oauth_header_access_params = "OAuth realm=\"test\","\
            "oauth_consumer_key=\"%s\","\
            "oauth_token=\"%s\","\
            "oauth_signature_method=\"PLAINTEXT\","\
            "oauth_signature=\"%s&%s\","\
            "oauth_timestamp=\"%s\","\
            "oauth_nonce=\"accessnonce\","\
            "oauth_version=\"1.0\","\
            "oauth_verifier=\"%s\"" % (self.consumer.key,token.key,self.consumer.secret,token.secret,str(int(time.time())),token.verifier)

        access_resp = self.client.get("/XAPI/OAuth/token/", Authorization=oauth_header_access_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(access_resp.status_code, 200)
        access_token = models.Token.objects.filter(token_type=models.Token.ACCESS, consumer=self.consumer)[0]
        self.assertIn(access_token.key, access_resp.content)
        self.assertEqual(access_token.user.username, u'jane')

        # Test same Nonce
        access_resp = self.client.get("/XAPI/OAuth/token/", Authorization=oauth_header_access_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(access_resp.status_code, 401)
        self.assertEqual(access_resp.content, 'Nonce already used: accessnonce')

        # Test missing/invalid verifier
        oauth_header_access_params += ',oauth_nonce="yetanotheraccessnonce"'
        oauth_header_access_params += ',oauth_verifier="invalidverifier"'
        access_resp = self.client.get("/XAPI/OAuth/token/", Authorization=oauth_header_access_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(access_resp.status_code, 401)
        self.assertEqual(access_resp.content, 'Consumer key or token key does not match. Make sure your request token is approved. Check your verifier too if you use OAuth 1.0a.')     
        oauth_header_access_params += ',oauth_verifier="token.verifier"'

        # Test token not approved
        oauth_header_access_params += ',oauth_nonce="anotheraccessnonce"'
        token.is_approved = False
        token.save()
        access_resp = self.client.get("/XAPI/OAuth/token/", Authorization=oauth_header_access_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(access_resp.status_code, 401)
        self.assertEqual(access_resp.content, 'Consumer key or token key does not match. Make sure your request token is approved. Check your verifier too if you use OAuth 1.0a.')

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

        oauth_request = OAuthRequest.from_token_and_callback(access_token,
            http_url='http://testserver/XAPI/statements/', parameters=oauth_header_resource_params_dict)
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature
        resp = self.client.get("/XAPI/statements/", Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, '{"statements": [], "more": ""}')

        # Test wrong signature
        oauth_header_resource_params += ',oauth_signature="wrongsignature"'
        oauth_header_resource_params += ',oauth_nonce="anotheraccessresourcenonce"'
        resp = self.client.get("/XAPI/statements/", Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 401)
        self.assertIn('Invalid signature.', resp.content)

        # Test wrong params - will not return 'Invalid request parameters.' like oauth example states
        # because there is no Authorization header. With no auth header the lrs reads as no auth supplied at all
        resp = self.client.get("/XAPI/statements/", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.content, 'Auth is enabled but no authentication was sent with the request.')

        # Test revoke access
        access_token.delete()
        oauth_header_resource_params += ',oauth_signature="%s"' % signature
        oauth_header_resource_params += ',oauth_nonce="yetanotheraccessresourcenonce"'
        resp = self.client.get("/XAPI/statements/", Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 401)
        self.assertIn('Invalid access token', resp.content)

    def test_oauth_disabled(self):
        # Disable oauth
        if settings.OAUTH_ENABLED:
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
        path = "%s?%s" % ("/XAPI/OAuth/initiate", urllib.urlencode(param))                  
        request_resp = self.client.get(path, Authorization=oauth_header_request_params, X_Experience_API_Version="1.0.0")        
        self.assertEqual(request_resp.status_code, 400)
        self.assertEqual(request_resp.content,'OAuth is not enabled. To enable, set the OAUTH_ENABLED flag to true in settings' )

    def test_stmt_put(self):
        # build stmt data and path
        put_guid = str(uuid.uuid1())
        stmt = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bill"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/accessed","display": {"en-US":"accessed"}},
            "object": {"id":"act:test_put"}})
        param = {"statementId":put_guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))
        
        oauth_header_resource_params, access_token = self.perform_oauth_handshake(request_nonce='stmtputrequestnonce',
            access_nonce='stmtputaccessnonce', resource_nonce='stmtputresourcenonce')
        
        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add put data
        oauth_header_resource_params_dict.update(param)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='PUT',
            http_url=path, parameters=oauth_header_resource_params_dict)
        
        # build signature and add to the params
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        # Put statements
        resp = self.client.put(path, data=stmt, content_type="application/json",
            Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 204)

    def test_stmt_post_no_scope(self):

        stmt = {"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_post"}}
        stmt_json = json.dumps(stmt)

        oauth_header_resource_params, access_token = self.perform_oauth_handshake(scope=False,
            request_nonce='stmtpostrequestnonce', access_nonce='stmtpostaccessnonce',
            resource_nonce='stmtpostresourcenonce')

        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='POST',
            http_url='http://testserver/XAPI/statements/', parameters=oauth_header_resource_params_dict)

        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature  
        # print '\n' + oauth_header_resource_params
        post = self.client.post('/XAPI/statements/', data=stmt_json, content_type="application/json",
            Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 200)

    def test_stmt_simple_get(self):
        guid = str(uuid.uuid1())
        stmt = StatementManager(json.dumps({"id":guid,"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_simple_get"}}))
        param = {"statementId":guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))

        oauth_header_resource_params, access_token = self.perform_oauth_handshake(request_nonce='stmtgetrequestnonce',
            access_nonce='stmtgetaccessnonce', resource_nonce='stmtgetresourcenonce')

        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add get data
        oauth_header_resource_params_dict.update(param)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)

        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path,Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        rsp = resp.content
        self.assertIn(guid, rsp)

    def test_stmt_complex_get(self):
        stmt = StatementManager(json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_complex_get"}}))
        param = {"activity":"act:test_complex_get"}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))

        oauth_header_resource_params, access_token = self.perform_oauth_handshake(request_nonce='stmtcomplexrequestnonce',
            access_nonce='stmtcomplexaccessnonce', resource_nonce='stmtcomplexresourcenonce')

        # from_token_and_callback takes a dictionary 
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add get data
        oauth_header_resource_params_dict.update(param)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)

        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path,Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")        
        self.assertEqual(resp.status_code, 200)

    def test_stmt_get_then_wrong_scope(self):
        guid = str(uuid.uuid1())
        stmt = StatementManager(json.dumps({"id":guid,"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_simple_get"}}))
        param = {"statementId":guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))

        oauth_header_resource_params, access_token = self.perform_oauth_handshake(scope_type="statements/read,profile",
            request_nonce='stmtgetrequestnonce',access_nonce='stmtgetaccessnonce',
            resource_nonce='stmtgetresourcenonce')

        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add get data
        oauth_header_resource_params_dict.update(param)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)

        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path,Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        rsp = resp.content
        self.assertIn(guid, rsp)

        # Test POST (not allowed)
        post_stmt = {"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_post"}}
        post_stmt_json = json.dumps(post_stmt)

        # change nonce
        oauth_header_resource_params_dict['oauth_nonce'] = 'wrongpostnonce'
        # delete statementId from get
        del oauth_header_resource_params_dict['statementId']

        # create another oauth request
        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='POST',
            http_url='http://testserver/XAPI/statements/', parameters=oauth_header_resource_params_dict)
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature
        # replace headers with the nonce you added in dict
        new_oauth_headers = oauth_header_resource_params.replace('oauth_nonce="accessresourcenonce"','oauth_nonce="wrongpostnonce"')        

        post = self.client.post('/XAPI/statements/', data=post_stmt_json, content_type="application/json",
            Authorization=new_oauth_headers, X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 403)
        self.assertEqual(post.content, 'Incorrect permissions to POST at /statements')

    def test_activity_state_put_then_wrong_scope(self):
        url = 'http://testserver/XAPI/activities/state'
        testagent = '{"name":"jane","mbox":"mailto:jane@example.com"}'
        activityId = "http://www.iana.org/domains/example/"
        stateId = "id:the_state_id"
        activity = models.Activity(activity_id=activityId)
        activity.save()
        testparams = {"stateId": stateId, "activityId": activityId, "agent": testagent}
        teststate = {"test":"put activity state 1"}
        path = '%s?%s' % (url, urllib.urlencode(testparams))

        oauth_header_resource_params, access_token = self.perform_oauth_handshake(scope_type='state',
            request_nonce='stateforbiddenrequestnonce', access_nonce='stateforbiddenaccessnonce',
            resource_nonce='stateforbiddenresourcenonce')

        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add put data
        oauth_header_resource_params_dict.update(testparams)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='PUT',
            http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        put = self.client.put(path, data=teststate, content_type="application/json",
            Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(put.status_code, 204)
        
        # Set up for Get
        guid = str(uuid.uuid1())
        stmt = StatementManager(json.dumps({"id":guid,"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_simple_get"}}))
        param = {"statementId":guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))

        # change nonce
        oauth_header_resource_params_dict['oauth_nonce'] = 'differnonce'
        # delete statementId from get
        del oauth_header_resource_params_dict['stateId']
        del oauth_header_resource_params_dict['activityId']
        del oauth_header_resource_params_dict['agent']                
        # update dict with stmt data
        oauth_header_resource_params_dict.update(param)

        # create another oauth request
        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature2 = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params_new = oauth_header_resource_params.replace('"%s"' % signature, '"%s"' % signature2) 
        # replace headers with the nonce you added in dict
        new_oauth_headers = oauth_header_resource_params_new.replace('oauth_nonce="accessresourcenonce"','oauth_nonce="differnonce"')        
        get = self.client.get(path, content_type="application/json",
            Authorization=new_oauth_headers, X_Experience_API_Version="1.0.0")

        self.assertEqual(get.status_code, 403)
        self.assertEqual(get.content, 'Incorrect permissions to GET at /statements')



    def stmt_get_then_wrong_profile_scope(self):
        guid = str(uuid.uuid1())
        stmt = StatementManager(json.dumps({"id":guid,"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_simple_get"}}))
        param = {"statementId":guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))

        oauth_header_resource_params, access_token = self.perform_oauth_handshake(scope_type="statements/read",
            request_nonce='stmtgetrequestnonce',access_nonce='stmtgetaccessnonce',
            resource_nonce='stmtgetresourcenonce')

        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add get data
        oauth_header_resource_params_dict.update(param)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)

        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path,Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        rsp = resp.content
        self.assertIn(guid, rsp)

        url = 'http://testserver/XAPI/agents/profile'
        params = {"agent": {"mbox":"mailto:test@example.com"}}
        path = "%s?%s" %(url, urllib.urlencode(params))

        oauth_header_resource_params_dict['oauth_nonce'] = 'differnonce'
        del oauth_header_resource_params_dict['statementId']
        oauth_header_resource_params_dict.update(params)
        # create another oauth request
        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)

        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature2 = signature_method.build_signature(oauth_request, self.consumer, access_token)
        
        new_sig_params = oauth_header_resource_params.replace('"%s"' % signature, '"%s"' % signature2 )
        # replace headers with the nonce you added in dict
        new_oauth_headers = new_sig_params.replace('oauth_nonce="accessresourcenonce"','oauth_nonce="differnonce"')        
        r = self.client.get(path, Authorization=new_oauth_headers, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)


    def test_consumer_state(self):
        stmt = StatementManager(json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_complex_get"}}))
        param = {"object":{"objectType": "Activity", "id":"act:test_complex_get"}}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))

        oauth_header_resource_params, access_token = self.perform_oauth_handshake(request_nonce='consumerstaterequestnonce',
            access_nonce='consumerstateaccessnonce', resource_nonce='consumerstateresourcenonce')

        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add get data
        oauth_header_resource_params_dict.update(param)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        consumer = access_token.consumer
        consumer.status = 4
        consumer.save()
        resp = self.client.get(path,Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")        
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.content, 'test client has not been authorized')

    def test_simple_stmt_get_mine_only(self):
        guid = str(uuid.uuid1())

        username = "tester1"
        email = "test1@tester.com"
        password = "test"
        auth = "Basic %s" % base64.b64encode("%s:%s" % (username, password))
        form = {"username":username, "email":email,"password":password,"password2":password}
        response = self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0.0")

        param = {"statementId":guid}
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode(param))
        stmt = json.dumps({"verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_put"},"actor":{"objectType":"Agent", "mbox":"mailto:t@t.com"}})

        putResponse = self.client.put(path, stmt, content_type="application/json", Authorization=auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(putResponse.status_code, 204)
        
        param = {"statementId":guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))

        oauth_header_resource_params, access_token = self.perform_oauth_handshake(scope_type="statements/read/mine",
            request_nonce='stmtgetrequestnonce',access_nonce='stmtgetaccessnonce', resource_nonce='stmtgetresourcenonce')

        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add get data
        oauth_header_resource_params_dict.update(param)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)

        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path,Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 403)

        # build stmt data and path
        oauth_agent1 = models.Agent.objects.get(account_name=self.consumer.key)
        oauth_agent2 = models.Agent.objects.get(mbox="mailto:test1@tester.com")
        oauth_group = models.Agent.objects.get(member__in=[oauth_agent1, oauth_agent2])
        guid = str(uuid.uuid1())

        stmt = StatementManager(json.dumps({"id":guid,"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bill"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/accessed","display": {"en-US":"accessed"}},
            "object": {"id":"act:test_put"}, "authority":oauth_group.get_agent_json()}))
        param = {"statementId":guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))
        
        # add put data
        oauth_header_resource_params_dict['statementId'] = guid
        oauth_header_resource_params_dict['oauth_nonce'] = 'getdiffernonce'

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)
        
        # build signature and add to the params
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        get_signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        replace_sig = oauth_header_resource_params.replace('"%s"' % signature, '"%s"' % get_signature)
        new_oauth_headers = replace_sig.replace('oauth_nonce="accessresourcenonce"','oauth_nonce="getdiffernonce"')        

        # Put statements
        get = self.client.get(path, content_type="application/json",
            Authorization=new_oauth_headers, X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)

    def test_complex_stmt_get_mine_only(self):
        guid = str(uuid.uuid1())
        username = "tester1"
        email = "test1@tester.com"
        password = "test"
        auth = "Basic %s" % base64.b64encode("%s:%s" % (username, password))
        form = {"username":username, "email":email,"password":password,"password2":password}
        response = self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0.0")

        param = {"statementId":guid}
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode(param))
        stmt = json.dumps({"verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_put"},"actor":{"objectType":"Agent", "mbox":"mailto:t@t.com"}})

        putResponse = self.client.put(path, stmt, content_type="application/json", Authorization=auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(putResponse.status_code, 204)

        param = {"statementId":guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))

        oauth_header_resource_params, access_token = self.perform_oauth_handshake(scope_type="statements/read/mine",
            request_nonce='stmtgetrequestnonce',access_nonce='stmtgetaccessnonce', resource_nonce='stmtgetresourcenonce')

        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add get data
        oauth_header_resource_params_dict.update(param)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)

        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        resp = self.client.get(path,Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 403)

        # build stmt data and path
        oauth_agent1 = models.Agent.objects.get(account_name=self.consumer.key)
        oauth_agent2 = models.Agent.objects.get(mbox="mailto:test1@tester.com")
        oauth_group = models.Agent.objects.get(member__in=[oauth_agent1, oauth_agent2])
        guid = str(uuid.uuid1())

        stmt = StatementManager(json.dumps({"id":guid,"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bill"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/accessed","display": {"en-US":"accessed"}},
            "object": {"id":"act:test_put"}, "authority":oauth_group.get_agent_json()}))
        
        # add put data
        oauth_header_resource_params_dict['oauth_nonce'] = 'getdiffernonce'
        del oauth_header_resource_params_dict['statementId']
        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url='http://testserver/XAPI/statements', parameters=oauth_header_resource_params_dict)
        
        # build signature and add to the params
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        get_signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        replace_sig = oauth_header_resource_params.replace('"%s"' % signature, '"%s"' % get_signature)
        new_oauth_headers = replace_sig.replace('oauth_nonce="accessresourcenonce"','oauth_nonce="getdiffernonce"')        

        # Put statements
        get = self.client.get('http://testserver/XAPI/statements', content_type="application/json",
            Authorization=new_oauth_headers, X_Experience_API_Version="1.0.0")
        get_content = json.loads(get.content)

        self.assertEqual(get.status_code, 200)
        self.assertEqual(get_content['statements'][0]['actor']['name'], 'bill')
        self.assertEqual(len(get_content['statements']), 1)

    def test_state_wrong_auth(self):
        url = 'http://testserver/XAPI/activities/state'
        testagent = '{"name":"joe","mbox":"mailto:joe@example.com"}'
        activityId = "http://www.iana.org/domains/example/"
        stateId = "id:the_state_id"
        activity = models.Activity(activity_id=activityId)
        activity.save()
        testparams = {"stateId": stateId, "activityId": activityId, "agent": testagent}
        teststate = {"test":"put activity state 1"}
        path = '%s?%s' % (url, urllib.urlencode(testparams))

        oauth_header_resource_params, access_token = self.perform_oauth_handshake(scope_type='state',
            request_nonce='stateforbiddenrequestnonce', access_nonce='stateforbiddenaccessnonce',
            resource_nonce='stateforbiddenresourcenonce')

        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add put data
        oauth_header_resource_params_dict.update(testparams)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='PUT',
            http_url=path, parameters=oauth_header_resource_params_dict)
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        put = self.client.put(path, data=teststate, content_type="application/json",
            Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")

        self.assertEqual(put.status_code, 404)        
        self.assertEqual(put.content, "Agent in state cannot be found to match user in authorization")

    def test_profile_wrong_auth(self):
        agent = models.Agent(name="joe", mbox="mailto:joe@example.com")
        agent.save()

        url = 'http://testserver/XAPI/agents/profile'
        testparams = {"agent": '{"name":"joe","mbox":"mailto:joe@example.com"}'}
        path = '%s?%s' % (url, urllib.urlencode(testparams))

        oauth_header_resource_params, access_token = self.perform_oauth_handshake(scope_type='profile',
            request_nonce='profileforbiddenrequestnonce', access_nonce='profileforbiddenaccessnonce',
            resource_nonce='profileforbiddenresourcenonce')

        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add put data
        oauth_header_resource_params_dict.update(testparams)
        
        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)

        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        get = self.client.get(path, content_type="application/json",
            Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")

        self.assertEqual(get.status_code, 403)
        self.assertEqual(get.content, "Authorization doesn't match agent in profile")

    def test_define_scope_activity(self):
        url = 'http://testserver/XAPI/statements'
        guid = str(uuid.uuid1())
        existing_stmt = StatementManager(json.dumps({"id":guid,"actor":{"objectType": "Agent",
            "mbox":"mailto:bob@bob.com", "name":"bob"},"verb":{"id": "http://adlnet.gov/expapi/verbs/passed",
            "display": {"en-US":"passed"}},"object": {"id":"test://test/define/scope"}}))

        # build stmt data and path
        put_guid = str(uuid.uuid1())
        stmt = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:bill@bill.com", "name":"bill"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/accessed","display": {"en-US":"accessed"}},
            "object": {"id":"test://test/define/scope",
            'definition': {'name': {'en-US':'testname', 'en-GB': 'altname'},
            'description': {'en-US':'testdesc', 'en-GB': 'altdesc'},'type': 'type:course',
            'interactionType': 'other'}}})

        param = {"statementId":put_guid}
        path = "%s?%s" % (url, urllib.urlencode(param))
        
        # START PUT STMT
        oauth_header_resource_params, access_token = self.perform_oauth_handshake(scope_type='statements/write,statements/read',
            request_nonce='anotherstmtputrequestnonce',access_nonce='anotherstmtputaccessnonce',
            resource_nonce='anotherstmtputresourcenonce')
        
        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add put data
        oauth_header_resource_params_dict.update(param)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='PUT',
            http_url=path, parameters=oauth_header_resource_params_dict)
        
        # build signature and add to the params
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature
        # Put statements - does not have define scope, therefore it creates another activity with 
        # global_representation as false
        resp = self.client.put(path, data=stmt, content_type="application/json",
            Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")

        self.assertEqual(resp.status_code, 204)
        acts = models.Activity.objects.all()
        self.assertEqual(len(acts), 2)
        self.assertEqual(acts[0].activity_id, acts[1].activity_id)

        # START GET STMT
        get_params = {"activity":"test://test/define/scope"}
        path = "%s?%s" % (url, urllib.urlencode(get_params)) 

        del oauth_header_resource_params_dict['statementId']
        oauth_header_resource_params_dict.update(get_params)
        oauth_header_resource_params_dict['oauth_nonce'] = 'getdiffernonce'

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)
        
        # build signature and add to the params
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        get_signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        replace_sig = oauth_header_resource_params.replace('"%s"' % signature, '"%s"' % get_signature)
        new_oauth_headers = replace_sig.replace('oauth_nonce="accessresourcenonce"','oauth_nonce="getdiffernonce"')        

        get_resp = self.client.get(path, X_Experience_API_Version="1.0.0",
            Authorization=new_oauth_headers)
        self.assertEqual(get_resp.status_code, 200)
        content = json.loads(get_resp.content)
        self.assertEqual(len(content['statements']), 2)
        self.client.logout()

        # START OF POST WITH ANOTHER HANDSHAKE
        post_stmt = {"actor":{"objectType": "Agent", "mbox":"mailto:dom@dom.com", "name":"dom"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/tested","display": {"en-US":"tested"}},
            "object": {"id":"test://test/define/scope",
            'definition': {'name': {'en-US':'definename', 'en-GB': 'definealtname'},
            'description': {'en-US':'definedesc', 'en-GB': 'definealtdesc'},'type': 'type:course',
            'interactionType': 'other'}}}
        stmt_json = json.dumps(post_stmt)

        post_oauth_header_resource_params, post_access_token = self.perform_oauth_handshake2(scope_type='define,statements/write',
            request_nonce='stmtpostrequestnonce', access_nonce='stmtpostaccessnonce',
            resource_nonce='stmtpostresourcenonce')

        # from_token_and_callback takes a dictionary        
        post_param_list = post_oauth_header_resource_params.split(",")
        post_oauth_header_resource_params_dict = {}
        for p in post_param_list:
            item = p.split("=")
            post_oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del post_oauth_header_resource_params_dict['OAuth realm']
        
        post_oauth_request = OAuthRequest.from_token_and_callback(post_access_token, http_method='POST',
            http_url='http://testserver/XAPI/statements/',
            parameters=post_oauth_header_resource_params_dict)

        post_signature_method = OAuthSignatureMethod_HMAC_SHA1()
        post_signature = signature_method.build_signature(post_oauth_request, self.consumer2,
            post_access_token)

        post_oauth_header_resource_params += ',oauth_signature="%s"' % post_signature  
        # This adds the act_def to the very first activity created in this test sine this has define scope
        post = self.client.post('/XAPI/statements/', data=stmt_json, content_type="application/json",
            Authorization=post_oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 200)
        acts = models.Activity.objects.all()
        self.assertEqual(len(acts), 2)

        global_act = models.Activity.objects.get(global_representation=True)        
        global_name_list = global_act.activity_definition_name.values()
        self.assertIn('definename', global_name_list)
        self.assertIn('definealtname', global_name_list)
        global_desc_list = global_act.activity_definition_description.values()
        self.assertIn('definedesc', global_desc_list)
        self.assertIn('definealtdesc', global_desc_list)

        non_global_act = models.Activity.objects.get(global_representation=False)        
        non_global_name_list = non_global_act.activity_definition_name.values()
        self.assertIn('testname', non_global_name_list)
        self.assertIn('altname', non_global_name_list)
        non_global_desc_list = non_global_act.activity_definition_description.values()
        self.assertIn('testdesc', non_global_desc_list)
        self.assertIn('altdesc', non_global_desc_list)

    def test_define_scope_agent(self):
        url = 'http://testserver/XAPI/statements'
        guid = str(uuid.uuid1())
        existing_stmt = StatementManager(json.dumps({"id":guid,"actor":{"objectType": "Agent",
            "mbox":"mailto:bob@bob.com", "name":"bob"},"verb":{"id": "http://adlnet.gov/expapi/verbs/helped",
            "display": {"en-US":"helped"}},"object": {"objectType":"Agent", "mbox":"mailto:tim@tim.com",
            "name":"tim"}}))

        # build stmt data and path
        put_guid = str(uuid.uuid1())
        stmt = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:bill@bill.com", "name":"bill"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/talked","display": {"en-US":"talked"}},
            "object": {"objectType":"Agent", "mbox":"mailto:tim@tim.com","name":"tim timson"}})

        param = {"statementId":put_guid}
        path = "%s?%s" % (url, urllib.urlencode(param))
        
        # START PUT STMT
        oauth_header_resource_params, access_token = self.perform_oauth_handshake(scope_type='statements/write,statements/read',
            request_nonce='anotherstmtputrequestnonce',access_nonce='anotherstmtputaccessnonce',
            resource_nonce='anotherstmtputresourcenonce')
        
        # from_token_and_callback takes a dictionary        
        param_list = oauth_header_resource_params.split(",")
        oauth_header_resource_params_dict = {}
        for p in param_list:
            item = p.split("=")
            oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del oauth_header_resource_params_dict['OAuth realm']
        # add put data
        oauth_header_resource_params_dict.update(param)

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='PUT',
            http_url=path, parameters=oauth_header_resource_params_dict)
        
        # build signature and add to the params
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        oauth_header_resource_params += ',oauth_signature="%s"' % signature

        # Put statements
        resp = self.client.put(path, data=stmt, content_type="application/json",
            Authorization=oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 204)
        agents = models.Agent.objects.all().values_list('name', flat=True)
        # Jane, Anonymous agent for account, Group for jane and account, bill, bob, tim, tim timson
        self.assertEqual(len(agents), 7)
        self.assertIn('tim', agents)
        self.assertIn('tim timson', agents)
        tim = models.Agent.objects.get(name='tim timson')
        self.assertFalse(tim.global_representation)
        tim = models.Agent.objects.get(name='tim')
        self.assertTrue(tim.global_representation)

        # START GET STMT
        get_params = {"agent":{"objectType": "Agent", "mbox":"mailto:tim@tim.com"}, "related_agents":True}
        path = "%s?%s" % (url, urllib.urlencode(get_params)) 

        del oauth_header_resource_params_dict['statementId']
        oauth_header_resource_params_dict.update(get_params)
        oauth_header_resource_params_dict['oauth_nonce'] = 'getdiffernonce'

        oauth_request = OAuthRequest.from_token_and_callback(access_token, http_method='GET',
            http_url=path, parameters=oauth_header_resource_params_dict)
        
        # build signature and add to the params
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        get_signature = signature_method.build_signature(oauth_request, self.consumer, access_token)
        replace_sig = oauth_header_resource_params.replace('"%s"' % signature, '"%s"' % get_signature)
        new_oauth_headers = replace_sig.replace('oauth_nonce="accessresourcenonce"','oauth_nonce="getdiffernonce"')        

        get_resp = self.client.get(path, X_Experience_API_Version="1.0.0",
            Authorization=new_oauth_headers)
        self.assertEqual(get_resp.status_code, 200)
        content = json.loads(get_resp.content)
        # Should only be one since querying by tim email. Will only pick up global tim object
        self.assertEqual(len(content['statements']), 1)
        self.client.logout()
        
        # START OF POST WITH ANOTHER HANDSHAKE
        ot = "Group"
        members = [{"name":"john doe","mbox":"mailto:jd@example.com"},
                    {"name":"jan doe","mbox":"mailto:jandoe@example.com"}]
        kwargs = {"objectType":ot, "member": members, "name": "doe group"}
        global_group, created = models.Agent.objects.gen(**kwargs)

        members = [{"name":"john doe","mbox":"mailto:jd@example.com"},
                    {"name":"jan doe","mbox":"mailto:jandoe@example.com"},
                    {"name":"dave doe", "mbox":"mailto:dd@example.com"}]
        kwargs1 = {"objectType":ot, "member": members, "name": "doe group"}

        post_stmt = {"actor":{"objectType": "Agent", "mbox":"mailto:dom@dom.com", "name":"dom"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/assisted","display": {"en-US":"assisted"}},
            "object": kwargs1}
        stmt_json = json.dumps(post_stmt)

        post_oauth_header_resource_params, post_access_token = self.perform_oauth_handshake2(scope_type='statements/write,statements/read',
            request_nonce='stmtpostrequestnonce', access_nonce='stmtpostaccessnonce',
            resource_nonce='stmtpostresourcenonce')

        # from_token_and_callback takes a dictionary        
        post_param_list = post_oauth_header_resource_params.split(",")
        post_oauth_header_resource_params_dict = {}
        for p in post_param_list:
            item = p.split("=")
            post_oauth_header_resource_params_dict[str(item[0]).strip()] = str(item[1]).strip('"')
        
        # from_request ignores realm, must remove so not input to from_token_and_callback
        del post_oauth_header_resource_params_dict['OAuth realm']
        
        post_oauth_request = OAuthRequest.from_token_and_callback(post_access_token, http_method='POST',
            http_url='http://testserver/XAPI/statements/',
            parameters=post_oauth_header_resource_params_dict)

        post_signature_method = OAuthSignatureMethod_HMAC_SHA1()
        post_signature = signature_method.build_signature(post_oauth_request, self.consumer2,
            post_access_token)

        post_oauth_header_resource_params += ',oauth_signature="%s"' % post_signature  
        
        post = self.client.post('/XAPI/statements/', data=stmt_json, content_type="application/json",
            Authorization=post_oauth_header_resource_params, X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 200)
        agents = models.Agent.objects.all()
        
        # These 5 agents are all non-global since created w/o define scope
        non_globals = models.Agent.objects.filter(global_representation=False).values_list('name', flat=True)
        self.assertEqual(len(non_globals), 5)
        self.assertIn('bill', non_globals)
        self.assertIn('tim timson', non_globals)
        self.assertIn('dave doe', non_globals)
        self.assertIn('dom', non_globals)
        self.assertIn('doe group', non_globals)
        # 2 oauth group objects, all of these agents since created with member or manually and 2 anon
        # account agents for the accounts in the oauth groups
        global_agents = models.Agent.objects.filter(global_representation=True).values_list('name', flat=True)
        self.assertEqual(len(global_agents), 11)
        self.assertIn('bob', global_agents)
        self.assertIn('tim', global_agents)
        self.assertIn('jan doe', global_agents)
        self.assertIn('john doe', global_agents)
        self.assertIn('jane', global_agents)
        self.assertIn('dick', global_agents)
        self.assertIn('doe group', global_agents)
