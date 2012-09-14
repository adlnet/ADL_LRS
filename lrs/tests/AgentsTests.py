from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import views
import json
from os import path
import sys
import base64

from lrs.objects import Agent

class AgentsTests(TestCase):
    def setUp(self):
        self.username = "tester"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {'username':self.username,'password':self.password,'password2':self.password}
        response = self.client.post(reverse(views.register),form)

    def test_get(self):
        agent = json.dumps({"name":["me"],"mbox":["mailto:me@example.com"]})
        me = Agent.Agent(agent,create=True)
        response = self.client.get(reverse(views.agents), {'agent':agent}, HTTP_AUTHORIZATION=self.auth)
        #print response
        self.assertContains(response, 'mailto:me@example.com')

    #def test_get_merge(self):
    #    agent = json.dumps({"name":["me"],"mbox":["mailto:me@example.com"]})
    #    response = self.client.get(reverse(views.agents), {'agent':agent})
    #    agent = json.dumps({"mbox":["mailto:me@example.com"]})
    #    response = self.client.get(reverse(views.agents), {'agent':agent})
    #    self.assertContains(response, 'mailto:me@example.com')
    #    self.assertContains(response, 'name')
    #    self.assertContains(response, 'me')
    
    def test_get_no_agent(self):
        response = self.client.get(reverse(views.agents), HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(response.status_code, 400)
    
    def test_post(self):
        agent = json.dumps({"name":["me"],"mbox":["mailto:me@example.com"]})
        response = self.client.post(reverse(views.agents), {'agent':agent},content_type='application/x-www-form-urlencoded', HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(response.status_code, 405)
