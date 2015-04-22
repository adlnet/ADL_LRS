import json
import urlparse
import datetime
import base64
import uuid
import urllib

from django.http import QueryDict
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.test import TestCase
from django.contrib.auth.models import User

from ..models import Activity
from ..views import statements

from oauth2_provider.provider import constants
from oauth2_provider.provider.utils import now as date_now
from oauth2_provider.provider.oauth2.forms import ClientForm
from oauth2_provider.provider.oauth2.models import Client, Grant, AccessToken, RefreshToken
from oauth2_provider.provider.oauth2.backends import BasicClientBackend, RequestParamsClientBackend, AccessTokenBackend

DEFAULT_SCOPE = "%s %s" % (constants.SCOPES[0][1], constants.SCOPES[1][1])

class OAuth2Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        print "\n%s-%s" % (__name__, cls.__name__)

    def login(self):
        if not settings.OAUTH_ENABLED:
            settings.OAUTH_ENABLED = True

        self.client.login(username='test-user-1', password='test')

    def auth_url(self):
        return reverse('oauth2:capture')

    def auth_url2(self):
        return reverse('oauth2:authorize')

    def redirect_url(self):
        return reverse('oauth2:redirect')

    def access_token_url(self):
        return reverse('oauth2:access_token')

    def get_client(self, cid=2):
        return Client.objects.get(id=cid)

    def get_grant(self):
        return Grant.objects.all()[0]

    def get_user(self):
        return User.objects.get(username='test-user-1')

    def get_password(self):
        return 'test'

    def _login_and_authorize(self, url_func=None, scope=None, cid=2):
        if url_func is None:
            url_func = lambda: self.auth_url() + '?client_id=%s&response_type=code&state=abc' % self.get_client(cid).client_id

        response = self.client.get(url_func())
        response = self.client.get(self.auth_url2())

        # LRS CHANGE - DON'T HAVE TO SUPPLY SCOPE HERE - SHOULD GET DEFAULTED
        if scope:
            response = self.client.post(self.auth_url2(), {'authorize': True, 'scope': scope})
        else:
            response = self.client.post(self.auth_url2(), {'authorize': True})
        self.assertEqual(302, response.status_code, response.content)
        self.assertTrue(self.redirect_url() in response['Location'])


class AuthorizationTest(OAuth2Tests):
    fixtures = ['test_oauth2']

    def setUp(self):
        self._old_login = settings.LOGIN_URL
        settings.LOGIN_URL = '/login/'

    def tearDown(self):
        settings.LOGIN_URL = self._old_login

    def test_authorization_requires_login(self):
        response = self.client.get(self.auth_url())

        # Login redirect
        self.assertEqual(302, response.status_code)
        self.assertEqual('/login/', urlparse.urlparse(response['Location']).path)

        self.login()
        response = self.client.get(self.auth_url())

        self.assertEqual(302, response.status_code)

        self.assertTrue(self.auth_url2() in response['Location'])

    def test_authorization_requires_client_id(self):
        self.login()
        response = self.client.get(self.auth_url())
        response = self.client.get(self.auth_url2())

        self.assertEqual(400, response.status_code)
        self.assertTrue("An unauthorized client tried to access your resources." in response.content)

    def test_authorization_rejects_invalid_client_id(self):
        self.login()
        response = self.client.get(self.auth_url() + '?client_id=123')
        response = self.client.get(self.auth_url2())

        self.assertEqual(400, response.status_code)
        self.assertTrue("An unauthorized client tried to access your resources." in response.content)

    def test_authorization_requires_response_type(self):
        self.login()
        response = self.client.get(self.auth_url() + '?client_id=%s' % self.get_client().client_id)
        response = self.client.get(self.auth_url2())

        self.assertEqual(400, response.status_code)
        self.assertTrue(escape(u"No 'response_type' supplied.") in response.content)

    def test_authorization_requires_supported_response_type(self):
        self.login()
        response = self.client.get(self.auth_url() + '?client_id=%s&response_type=unsupported' % self.get_client().client_id)
        response = self.client.get(self.auth_url2())

        self.assertEqual(400, response.status_code)
        self.assertTrue(escape(u"'unsupported' is not a supported response type.") in response.content)

        response = self.client.get(self.auth_url() + '?client_id=%s&response_type=code' % self.get_client().client_id)
        response = self.client.get(self.auth_url2())
        self.assertEqual(200, response.status_code, response.content)

        response = self.client.get(self.auth_url() + '?client_id=%s&response_type=token' % self.get_client().client_id)
        response = self.client.get(self.auth_url2())
        self.assertEqual(200, response.status_code)

    def test_authorization_requires_a_valid_redirect_uri(self):
        self.login()

        response = self.client.get(self.auth_url() + '?client_id=%s&response_type=code&redirect_uri=%s' % (
            self.get_client().client_id,
            self.get_client().redirect_uri + '-invalid'))
        response = self.client.get(self.auth_url2())

        self.assertEqual(400, response.status_code)
        self.assertTrue(escape(u"The requested redirect didn't match the client settings.") in response.content)

        response = self.client.get(self.auth_url() + '?client_id=%s&response_type=code&redirect_uri=%s' % (
            self.get_client().client_id,
            self.get_client().redirect_uri))
        response = self.client.get(self.auth_url2())

        self.assertEqual(200, response.status_code)

    def test_authorization_requires_a_valid_scope(self):
        self.login()

        response = self.client.get(self.auth_url() + '?client_id=%s&response_type=code&scope=invalid+invalid2' % self.get_client().client_id)
        response = self.client.get(self.auth_url2())

        self.assertEqual(400, response.status_code)
        self.assertTrue(escape(u"'invalid' is not a valid scope.") in response.content)

        response = self.client.get(self.auth_url() + '?client_id=%s&response_type=code&scope=%s' % (
            self.get_client().client_id,
            constants.SCOPES[0][1]))
        response = self.client.get(self.auth_url2())
        self.assertEqual(200, response.status_code)

    def test_authorization_is_not_granted(self):
        self.login()

        response = self.client.get(self.auth_url() + '?client_id=%s&response_type=code' % self.get_client().client_id)
        response = self.client.get(self.auth_url2())

        response = self.client.post(self.auth_url2(), {'authorize': False, 'scope': constants.SCOPES[0][1]})
        self.assertEqual(302, response.status_code, response.content)
        self.assertTrue(self.redirect_url() in response['Location'])

        response = self.client.get(self.redirect_url())

        self.assertEqual(302, response.status_code)
        self.assertTrue('error=access_denied' in response['Location'])
        self.assertFalse('code' in response['Location'])

    def test_authorization_is_granted(self):
        self.login()

        self._login_and_authorize()

        response = self.client.get(self.redirect_url())

        self.assertEqual(302, response.status_code)
        self.assertFalse('error' in response['Location'])
        self.assertTrue('code' in response['Location'])

    def test_preserving_the_state_variable(self):
        self.login()

        self._login_and_authorize()

        response = self.client.get(self.redirect_url())

        self.assertEqual(302, response.status_code)
        self.assertFalse('error' in response['Location'])
        self.assertTrue('code' in response['Location'])
        self.assertTrue('state=abc' in response['Location'])

    def test_redirect_requires_valid_data(self):
        self.login()
        response = self.client.get(self.redirect_url())
        self.assertEqual(400, response.status_code)


class AccessTokenTest(OAuth2Tests):
    fixtures = ['test_oauth2.json']

    def get_user_auth(self):
        return  "Basic %s" % base64.b64encode("%s:%s" % ("test-user-1", "test"))

    def test_access_token_get_expire_delta_value(self):
        user = self.get_user()
        client = self.get_client()
        token = AccessToken.objects.create(user=user, client=client)
        now = date_now()
        default_expiration_timedelta = constants.EXPIRE_DELTA
        current_expiration_timedelta = datetime.timedelta(seconds=token.get_expire_delta(reference=now))
        self.assertTrue(abs(current_expiration_timedelta - default_expiration_timedelta) <= datetime.timedelta(seconds=1))

    def test_fetching_access_token_with_invalid_client(self):
        self.login()
        self._login_and_authorize()

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'authorization_code',
            'client_id': self.get_client().client_id + '123',
            'client_secret': self.get_client().client_secret, })

        self.assertEqual(400, response.status_code, response.content)
        self.assertEqual('invalid_client', json.loads(response.content)['error'])

    def test_fetching_access_token_with_invalid_grant(self):
        self.login()
        self._login_and_authorize()

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'authorization_code',
            'client_id': self.get_client().client_id,
            'client_secret': self.get_client().client_secret,
            'code': '123'})

        self.assertEqual(400, response.status_code, response.content)
        self.assertEqual('invalid_grant', json.loads(response.content)['error'])


    def _login_authorize_get_token(self, scope=DEFAULT_SCOPE, cid=2):
        required_props = ['access_token', 'token_type']

        self.login()
        self._login_and_authorize(url_func=None, scope=scope, cid=cid)

        response = self.client.get(self.redirect_url())
        query = QueryDict(urlparse.urlparse(response['Location']).query)
        code = query['code']

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'authorization_code',
            'client_id': self.get_client(cid).client_id,
            'client_secret': self.get_client(cid).client_secret,
            'code': code})

        self.assertEqual(200, response.status_code, response.content)

        token = json.loads(response.content)

        for prop in required_props:
            self.assertIn(prop, token, "Access token response missing "
                    "required property: %s" % prop)

        return token

    def test_get_statements_user_submitted(self):
        token = self._login_authorize_get_token()

        stmt = json.dumps({"verb":{"id": "http://adlnet.gov/expapi/verbs/created",
            "display": {"en-US":"created"}}, "object": {"id":"act:activity"},
            "actor":{"objectType":"Agent","mbox":"mailto:s@s.com"}})
        response = self.client.post(reverse(statements), stmt, content_type="application/json",
            Authorization=self.get_user_auth(), X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)


        stmt_get = self.client.get(reverse(statements), X_Experience_API_Version=settings.XAPI_VERSION, Authorization="Bearer " + token['access_token'], content_type="application/json")
        self.assertEqual(stmt_get.status_code, 200)
        stmts = json.loads(stmt_get.content)['statements']
        self.assertEqual(len(stmts), 1)

    def test_get_statements_oauth_submitted(self):
        token = self._login_authorize_get_token()

        stmt = json.dumps({"verb":{"id": "http://adlnet.gov/expapi/verbs/created",
            "display": {"en-US":"created"}}, "object": {"id":"act:activity"},
            "actor":{"objectType":"Agent","mbox":"mailto:s@s.com"}})
        response = self.client.post(reverse(statements), stmt, content_type="application/json",
            Authorization="Bearer " + token['access_token'], X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)

        stmt_get = self.client.get(reverse(statements), X_Experience_API_Version=settings.XAPI_VERSION, Authorization="Bearer " + token['access_token'], content_type="application/json")
        self.assertEqual(stmt_get.status_code, 200)
        stmts = json.loads(stmt_get.content)['statements']
        self.assertEqual(len(stmts), 1)

    def test_get_statements_mix_submitted(self):
        token = self._login_authorize_get_token()

        stmt = json.dumps({"verb":{"id": "http://adlnet.gov/expapi/verbs/created",
            "display": {"en-US":"created"}}, "object": {"id":"act:activity"},
            "actor":{"objectType":"Agent","mbox":"mailto:s@s.com"}})
        response = self.client.post(reverse(statements), stmt, content_type="application/json",
            Authorization="Bearer " + token['access_token'], X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)

        stmt = json.dumps({"verb":{"id": "http://adlnet.gov/expapi/verbs/created",
            "display": {"en-US":"created"}}, "object": {"id":"act:activity"},
            "actor":{"objectType":"Agent","mbox":"mailto:s@s.com"}})
        response = self.client.post(reverse(statements), stmt, content_type="application/json",
            Authorization=self.get_user_auth(), X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)

        stmt_get = self.client.get(reverse(statements), X_Experience_API_Version=settings.XAPI_VERSION, Authorization="Bearer " + token['access_token'], content_type="application/json")
        self.assertEqual(stmt_get.status_code, 200)
        stmts = json.loads(stmt_get.content)['statements']
        self.assertEqual(len(stmts), 2)

        stmt_get = self.client.get(reverse(statements), X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.get_user_auth(), content_type="application/json")
        self.assertEqual(stmt_get.status_code, 200)
        stmts = json.loads(stmt_get.content)['statements']
        self.assertEqual(len(stmts), 2)

    def test_put_statements(self):
        token = self._login_authorize_get_token(scope=constants.SCOPES[0][1])

        put_guid = str(uuid.uuid1())
        stmt = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bill"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/accessed","display": {"en-US":"accessed"}},
            "object": {"id":"act:test_put"}})
        param = {"statementId":put_guid}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))

        resp = self.client.put(path, data=stmt, content_type="application/json",
            Authorization="Bearer " + token['access_token'], X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 204)        

    def test_post_statements(self):
        token = self._login_authorize_get_token()

        stmt = {"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_post"}}
        stmt_json = json.dumps(stmt)
        
        post = self.client.post('/XAPI/statements/', data=stmt_json, content_type="application/json",
            Authorization="Bearer " + token['access_token'], X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 200)

    def test_write_statements_wrong_scope(self):
        token = self._login_authorize_get_token(scope=constants.SCOPES[2][1])

        stmt = {"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_post"}}
        stmt_json = json.dumps(stmt)
        
        post = self.client.post('/XAPI/statements/', data=stmt_json, content_type="application/json",
            Authorization="Bearer " + token['access_token'], X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 403)

    def test_complex_statement_get(self):
        token = self._login_authorize_get_token()

        stmt_data = [{"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_complex_get"}, "authority":{"objectType":"Agent", "mbox":"mailto:jane@example.com"}},
            {"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {"id":"act:test_post"}}]
        stmt_post = self.client.post(reverse(statements), json.dumps(stmt_data), content_type="application/json",
            Authorization=self.get_user_auth(), X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        param = {"activity":"act:test_complex_get"}
        path = "%s?%s" % ('http://testserver/XAPI/statements', urllib.urlencode(param))

        resp = self.client.get(path,Authorization="Bearer " + token['access_token'], X_Experience_API_Version=settings.XAPI_VERSION)        
        self.assertEqual(resp.status_code, 200)
        stmts = json.loads(resp.content)['statements']
        self.assertEqual(len(stmts), 1)

    def test_define(self):
        stmt = {
                "actor":{
                    "objectType": "Agent",
                    "mbox":"mailto:t@t.com",
                    "name":"bob"
                },
                "verb":{
                    "id": "http://adlnet.gov/expapi/verbs/passed",
                    "display": {"en-US":"passed"}
                },
                "object":{
                    "id":"act:test_define",
                    'definition': {
                        'name': {'en-US':'testname'},
                        'description': {'en-US':'testdesc'},
                        'type': 'type:course'
                    }
                }
            }
        stmt_post = self.client.post(reverse(statements), json.dumps(stmt), content_type="application/json",
            Authorization=self.get_user_auth(), X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        token = self._login_authorize_get_token()

        stmt2 = {
                "actor":{
                    "objectType": "Agent",
                    "mbox":"mailto:t@t.com",
                    "name":"bob"
                },
                "verb":{
                    "id": "http://adlnet.gov/expapi/verbs/passed",
                    "display": {"en-US":"passed"}
                },
                "object":{
                    "id":"act:test_define",
                    'definition': {
                        'name': {'en-US':'testname differ'},
                        'description': {'en-US':'testdesc differ'},
                        'type': 'type:course'
                    }
                }
            }
        # Doesn't have define permission - should create another activity with that ID that isn't canonical
        stmt_post2 = self.client.post(reverse(statements), json.dumps(stmt2), content_type="application/json",
            Authorization="Bearer " + token['access_token'], X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post2.status_code, 200)
        acts = Activity.objects.filter(activity_id="act:test_define")
        self.assertEqual(len(acts), 2)

        stmt_post = self.client.post(reverse(statements), json.dumps(stmt), content_type="application/json",
            Authorization=self.get_user_auth(), X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post.status_code, 200)

        token2 = self._login_authorize_get_token(scope="%s %s" % (constants.SCOPES[0][1], constants.SCOPES[4][1]), cid=1)

        stmt3 = {
                "actor":{
                    "objectType": "Agent",
                    "mbox":"mailto:t@t.com",
                    "name":"bob"
                },
                "verb":{
                    "id": "http://adlnet.gov/expapi/verbs/passed",
                    "display": {"en-US":"passed"}
                },
                "object":{
                    "id":"act:test_define",
                    'definition': {
                        'name': {'en-US':'testname i define!'},
                        'description': {'en-US':'testdesc i define!'},
                        'type': 'type:course'
                    }
                }
            }
        # Doesn't have define permission - should create another activity with that ID that isn't canonical
        stmt_post3 = self.client.post(reverse(statements), json.dumps(stmt3), content_type="application/json",
            Authorization="Bearer " + token2['access_token'], X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(stmt_post3.status_code, 200)
        act_names = Activity.objects.filter(activity_id="act:test_define").values_list('activity_definition_name', flat=True)
        act_descs = Activity.objects.filter(activity_id="act:test_define").values_list('activity_definition_description', flat=True)
        self.assertEqual(len(act_names), 2)
        self.assertEqual(len(act_descs), 2)
        self.assertIn('{"en-US":"testname i define!"}', act_names)
        self.assertIn('{"en-US":"testdesc i define!"}', act_descs)

    def test_fetching_access_token_with_valid_grant(self):
        self._login_authorize_get_token()

    def test_fetching_access_token_with_invalid_grant_type(self):
        self.login()
        self._login_and_authorize()
        response = self.client.get(self.redirect_url())

        query = QueryDict(urlparse.urlparse(response['Location']).query)
        code = query['code']

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'invalid_grant_type',
            'client_id': self.get_client().client_id,
            'client_secret': self.get_client().client_secret,
            'code': code
        })

        self.assertEqual(400, response.status_code)
        self.assertEqual('unsupported_grant_type', json.loads(response.content)['error'],
            response.content)

    def test_fetching_single_access_token(self):
        constants.SINGLE_ACCESS_TOKEN = True

        result1 = self._login_authorize_get_token()
        result2 = self._login_authorize_get_token()

        self.assertEqual(result1['access_token'], result2['access_token'])

        constants.SINGLE_ACCESS_TOKEN = False

    def test_fetching_single_access_token_after_refresh(self):
        constants.SINGLE_ACCESS_TOKEN = True

        token = self._login_authorize_get_token()

        self.client.post(self.access_token_url(), {
            'grant_type': 'refresh_token',
            'refresh_token': token['refresh_token'],
            'client_id': self.get_client().client_id,
            'client_secret': self.get_client().client_secret,
        })

        new_token = self._login_authorize_get_token()
        self.assertNotEqual(token['access_token'], new_token['access_token'])

        constants.SINGLE_ACCESS_TOKEN = False

    def test_fetching_access_token_multiple_times(self):
        self._login_authorize_get_token()
        code = self.get_grant().code

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'authorization_code',
            'client_id': self.get_client().client_id,
            'client_secret': self.get_client().client_secret,
            'code': code})

        self.assertEqual(400, response.status_code)
        self.assertEqual('invalid_grant', json.loads(response.content)['error'])

    # LRS CHANGE - ACCORDING TO OAUTH2 SPEC, SHOULDN'T BE ABLE TO ESCALATE
    # THE SCOPE SINCE YOU CAN'T PASS IN SCOPE PARAM TO ACCESS TOKEN ENDPOINT
    # def test_escalating_the_scope(self):
    #     self.login()
    #     self._login_and_authorize()
    #     code = self.get_grant().code

    #     response = self.client.post(self.access_token_url(), {
    #         'grant_type': 'authorization_code',
    #         'client_id': self.get_client().client_id,
    #         'client_secret': self.get_client().client_secret,
    #         'code': code,
    #         'scope': constants.SCOPES[6][1]})

    #     self.assertEqual(400, response.status_code)
    #     self.assertEqual('invalid_scope', json.loads(response.content)['error'])

    def test_refreshing_an_access_token(self):
        token = self._login_authorize_get_token()

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'refresh_token',
            'refresh_token': token['refresh_token'],
            'client_id': self.get_client().client_id,
            'client_secret': self.get_client().client_secret,
        })

        self.assertEqual(200, response.status_code)

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'refresh_token',
            'refresh_token': token['refresh_token'],
            'client_id': self.get_client().client_id,
            'client_secret': self.get_client().client_secret,
        })

        self.assertEqual(400, response.status_code)
        self.assertEqual('invalid_grant', json.loads(response.content)['error'],
            response.content)

    def test_password_grant_public(self):
        c = self.get_client()
        c.client_type = 1 # public
        c.save()

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'password',
            'client_id': c.client_id,
            # No secret needed
            'username': self.get_user().username,
            'password': self.get_password(),
        })

        self.assertEqual(200, response.status_code, response.content)
        self.assertNotIn('refresh_token', json.loads(response.content))
        expires_in = json.loads(response.content)['expires_in']
        expires_in_days = round(expires_in / (60.0 * 60.0 * 24.0))
        self.assertEqual(expires_in_days, constants.EXPIRE_DELTA_PUBLIC.days)

    def test_password_grant_confidential(self):
        c = self.get_client()
        c.client_type = 0 # confidential
        c.save()

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'password',
            'client_id': c.client_id,
            'client_secret': c.client_secret,
            'username': self.get_user().username,
            'password': self.get_password(),
        })

        self.assertEqual(200, response.status_code, response.content)
        self.assertTrue(json.loads(response.content)['refresh_token'])

    def test_password_grant_confidential_no_secret(self):
        c = self.get_client()
        c.client_type = 0 # confidential
        c.save()

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'password',
            'client_id': c.client_id,
            'username': self.get_user().username,
            'password': self.get_password(),
        })

        self.assertEqual('invalid_client', json.loads(response.content)['error'])

    def test_password_grant_invalid_password_public(self):
        c = self.get_client()
        c.client_type = 1 # public
        c.save()

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'password',
            'client_id': c.client_id,
            'username': self.get_user().username,
            'password': self.get_password() + 'invalid',
        })

        self.assertEqual(400, response.status_code, response.content)
        self.assertEqual('invalid_client', json.loads(response.content)['error'])

    def test_password_grant_invalid_password_confidential(self):
        c = self.get_client()
        c.client_type = 0 # confidential
        c.save()

        response = self.client.post(self.access_token_url(), {
            'grant_type': 'password',
            'client_id': c.client_id,
            'client_secret': c.client_secret,
            'username': self.get_user().username,
            'password': self.get_password() + 'invalid',
        })

        self.assertEqual(400, response.status_code, response.content)
        self.assertEqual('invalid_grant', json.loads(response.content)['error'])

    def test_access_token_response_valid_token_type(self):
        token = self._login_authorize_get_token()
        self.assertEqual(token['token_type'], constants.TOKEN_TYPE, token)


class AuthBackendTest(OAuth2Tests):
    fixtures = ['test_oauth2']

    def test_basic_client_backend(self):
        request = type('Request', (object,), {'META': {}})()
        request.META['HTTP_AUTHORIZATION'] = "Basic " + "{0}:{1}".format(
            self.get_client().client_id,
            self.get_client().client_secret).encode('base64')

        self.assertEqual(BasicClientBackend().authenticate(request).id,
                         2, "Didn't return the right client.")

    def test_request_params_client_backend(self):
        request = type('Request', (object,), {'REQUEST': {}})()

        request.REQUEST['client_id'] = self.get_client().client_id
        request.REQUEST['client_secret'] = self.get_client().client_secret

        self.assertEqual(RequestParamsClientBackend().authenticate(request).id,
                         2, "Didn't return the right client.'")

    def test_access_token_backend(self):
        user = self.get_user()
        client = self.get_client()
        backend = AccessTokenBackend()
        token = AccessToken.objects.create(user=user, client=client)
        authenticated = backend.authenticate(access_token=token.token,
                client=client)

        self.assertIsNotNone(authenticated)


class EnforceSecureTest(OAuth2Tests):
    fixtures = ['test_oauth2']

    def setUp(self):
        constants.ENFORCE_SECURE = True

    def tearDown(self):
        constants.ENFORCE_SECURE = False

    def test_authorization_enforces_SSL(self):
        self.login()

        response = self.client.get(self.auth_url())

        self.assertEqual(400, response.status_code)
        self.assertTrue("A secure connection is required." in response.content)

    def test_access_token_enforces_SSL(self):
        response = self.client.post(self.access_token_url(), {})

        self.assertEqual(400, response.status_code)
        self.assertTrue("A secure connection is required." in response.content)

class ClientFormTest(TestCase):
    def test_client_form(self):
        form = ClientForm({'name': 'TestName', 'url': 'http://127.0.0.1:8000',
            'redirect_uri': 'http://localhost:8000/'})

        self.assertFalse(form.is_valid())

        form = ClientForm({
            'name': 'TestName',
            'url': 'http://127.0.0.1:8000',
            'redirect_uri': 'http://localhost:8000/',
            'client_type': constants.CLIENT_TYPES[0][0]})
        self.assertTrue(form.is_valid())
        form.save()

class DeleteExpiredTest(OAuth2Tests):
    fixtures = ['test_oauth2']

    def setUp(self):     
        self._delete_expired = constants.DELETE_EXPIRED
        constants.DELETE_EXPIRED = True

    def tearDown(self):
        constants.DELETE_EXPIRED = self._delete_expired

    def test_clear_expired(self):
        self.login()

        self._login_and_authorize()

        response = self.client.get(self.redirect_url())

        self.assertEqual(302, response.status_code)
        location = response['Location']
        self.assertFalse('error' in location)
        self.assertTrue('code' in location)

        # verify that Grant with code exists
        code = urlparse.parse_qs(location)['code'][0]
        self.assertTrue(Grant.objects.filter(code=code).exists())

        # use the code/grant
        response = self.client.post(self.access_token_url(), {
            'grant_type': 'authorization_code',
            'client_id': self.get_client().client_id,
            'client_secret': self.get_client().client_secret,
            'code': code})

        self.assertEquals(200, response.status_code)
        token = json.loads(response.content)
        self.assertTrue('access_token' in token)
        access_token = token['access_token']
        self.assertTrue('refresh_token' in token)
        refresh_token = token['refresh_token']

        # make sure the grant is gone
        self.assertFalse(Grant.objects.filter(code=code).exists())
        # and verify that the AccessToken and RefreshToken exist
        self.assertTrue(AccessToken.objects.filter(token=access_token)
                        .exists())
        self.assertTrue(RefreshToken.objects.filter(token=refresh_token)
                        .exists())

        # refresh the token
        response = self.client.post(self.access_token_url(), {
            'grant_type': 'refresh_token',
            'refresh_token': token['refresh_token'],
            'client_id': self.get_client().client_id,
            'client_secret': self.get_client().client_secret,      
        })
        self.assertEqual(200, response.status_code)
        token = json.loads(response.content)
        self.assertTrue('access_token' in token)
        self.assertNotEquals(access_token, token['access_token'])
        self.assertTrue('refresh_token' in token)
        self.assertNotEquals(refresh_token, token['refresh_token'])

        # make sure the orig AccessToken and RefreshToken are gone
        self.assertFalse(AccessToken.objects.filter(token=access_token)
                         .exists())
        self.assertFalse(RefreshToken.objects.filter(token=refresh_token)
                         .exists())