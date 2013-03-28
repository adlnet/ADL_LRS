from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import views
import json
from os import path
import sys
import base64

from lrs.models import agent

class AgentsTests(TestCase):
    def setUp(self):
        self.username = "tester"
        self.password = "test"
        self.email = "test@example.com"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {'username':self.username,'password':self.password,'password2':self.password, 'email':self.email}
        response = self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0")

    def test_get_no_agents(self):
        agent = json.dumps({"name":"me","mbox":"mailto:me@example.com"})
        response = self.client.get(reverse(views.agents), {'agent':agent}, Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(response.status_code, 404)

    def test_get(self):
        a = json.dumps({"name":"me","mbox":"mailto:me@example.com"})
        me = agent.objects.gen(**json.loads(a))
        response = self.client.get(reverse(views.agents), {'agent':a}, Authorization=self.auth, X_Experience_API_Version="1.0")
        r_data = json.loads(response.content)
        self.assertTrue(isinstance(r_data['mbox'], list))
        self.assertTrue(isinstance(r_data['name'], list))
        self.assertEqual(r_data['mbox'], ['mailto:me@example.com'])
        self.assertEqual(r_data['name'], ['me'])
        self.assertEqual(r_data['objectType'], 'Agent')

    def test_get_no_agent(self):
        response = self.client.get(reverse(views.agents), Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(response.status_code, 400)
    
    def test_post(self):
        agent = json.dumps({"name":"me","mbox":"mailto:me@example.com"})
        response = self.client.post(reverse(views.agents), {'agent':agent},content_type='application/x-www-form-urlencoded', Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(response.status_code, 405)
