import json
import base64
from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import views
from lrs.models import Agent

class AgentsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        print "\n%s" % __name__

    def setUp(self):
        self.username = "tester"
        self.password = "test"
        self.email = "test@example.com"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {'username':self.username,'password':self.password,'password2':self.password, 'email':self.email}
        self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0.0")

    def test_get_no_agents(self):
        agent = json.dumps({"name":"me","mbox":"mailto:me@example.com"})
        response = self.client.get(reverse(views.agents), {'agent':agent}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, "Error with Agent. The agent partial did not match any agents on record")

    def test_get(self):
        a = json.dumps({"name":"me","mbox":"mailto:me@example.com"})
        Agent.objects.retrieve_or_create(**json.loads(a))
        response = self.client.get(reverse(views.agents), {'agent':a}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        r_data = json.loads(response.content)
        self.assertTrue(isinstance(r_data['mbox'], list))
        self.assertTrue(isinstance(r_data['name'], list))
        self.assertEqual(r_data['mbox'], ['mailto:me@example.com'])
        self.assertEqual(r_data['name'], ['me'])
        self.assertEqual(r_data['objectType'], 'Person')
        self.assertIn('content-length', response._headers)

    def test_get_no_existing_agent(self):
        a = json.dumps({"mbox":"mailto:fail@fail.com"})
        response = self.client.get(reverse(views.agents), {'agent':a}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.content, 'Error with Agent. The agent partial did not match any agents on record')
        self.assertEqual(response.status_code, 404)

    def test_head(self):
        a = json.dumps({"name":"me","mbox":"mailto:me@example.com"})
        Agent.objects.retrieve_or_create(**json.loads(a))
        response = self.client.head(reverse(views.agents), {'agent':a}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.content, '')
        self.assertIn('content-length', response._headers)

    def test_get_no_agent(self):
        response = self.client.get(reverse(views.agents), Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 400)
    
    def test_post(self):
        agent = json.dumps({"name":"me","mbox":"mailto:me@example.com"})
        response = self.client.post(reverse(views.agents), {'agent':agent},content_type='application/x-www-form-urlencoded', Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 405)
