import json
import base64

from django.test import TestCase
from django.urls import reverse
from django.conf import settings

from ..models import Agent

from adl_lrs.views import register


class AgentTests(TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n%s" % __name__)
        super(AgentTests, cls).setUpClass()

    def setUp(self):
        self.username = "tester"
        self.password = "test"
        self.email = "test@example.com"
        self.auth = "Basic %s" % base64.b64encode(
            "%s:%s" % (self.username, self.password))
        form = {'username': self.username, 'password': self.password,
                'password2': self.password, 'email': self.email}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)

    def test_get_no_agents(self):
        agent = json.dumps({"name": "me", "mbox": "mailto:me@example.com"})
        response = self.client.get(reverse('lrs:agents'), {
                                   'agent': agent}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.content, "Error with Agent. The agent partial did not match any agents on record")

    def test_get(self):
        a = json.dumps({"name": "me", "mbox": "mailto:me@example.com"})
        Agent.objects.retrieve_or_create(**json.loads(a))
        response = self.client.get(reverse('lrs:agents'), {
                                   'agent': a}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        r_data = json.loads(response.content)
        self.assertTrue(isinstance(r_data['mbox'], list))
        self.assertTrue(isinstance(r_data['name'], list))
        self.assertEqual(r_data['mbox'], ['mailto:me@example.com'])
        self.assertEqual(r_data['name'], ['me'])
        self.assertEqual(r_data['objectType'], 'Person')
        self.assertIn('content-length', response._headers)

    def test_get_no_existing_agent(self):
        a = json.dumps({"mbox": "mailto:fail@fail.com"})
        response = self.client.get(reverse('lrs:agents'), {
                                   'agent': a}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(
            response.content, 'Error with Agent. The agent partial did not match any agents on record')
        self.assertEqual(response.status_code, 404)

    def test_get_bad_agent(self):
        a = json.dumps({})
        response = self.client.get(reverse('lrs:agents'), {
                                   'agent': a}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(
            response.content, 'One and only one of mbox, mbox_sha1sum, openid, account may be supplied with an Agent')
        self.assertEqual(response.status_code, 400)

    def test_head(self):
        a = json.dumps({"name": "me", "mbox": "mailto:me@example.com"})
        Agent.objects.retrieve_or_create(**json.loads(a))
        response = self.client.head(reverse('lrs:agents'), {
                                    'agent': a}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.content, '')
        self.assertIn('content-length', response._headers)

    def test_get_no_agent(self):
        response = self.client.get(reverse(
            'lrs:agents'), Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)

    def test_post(self):
        agent = json.dumps({"name": "me", "mbox": "mailto:me@example.com"})
        response = self.client.post(reverse('lrs:agents'), {
                                    'agent': agent}, content_type='application/x-www-form-urlencoded', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 405)
