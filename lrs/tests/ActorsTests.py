from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import views
import json
from os import path
import sys
import base64

from lrs.objects import Actor

class ActorsTests(TestCase):
    def setUp(self):
        self.username = "tester"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {'username':self.username,'password':self.password,'password2':self.password}
        response = self.client.post(reverse(views.register))

    def test_get_no_actors(self):
        actor = json.dumps({"name":["me"],"mbox":["mailto:me@example.com"]})
        response = self.client.get(reverse(views.actors), {'actor':actor}, Authorization=self.auth, X_Experience_API_Version="0.95")
        self.assertEqual(response.status_code, 404)

    def test_get(self):
        actor = json.dumps({"name":["me"],"mbox":["mailto:me@example.com"]})
        me = Actor.Actor(actor,create=True)
        response = self.client.get(reverse(views.actors), {'actor':actor}, Authorization=self.auth, X_Experience_API_Version="0.95")
        #print response
        self.assertContains(response, 'mailto:me@example.com')

    #def test_get_merge(self):
    #    actor = json.dumps({"name":["me"],"mbox":["mailto:me@example.com"]})
    #    response = self.client.get(reverse(views.actors), {'actor':actor})
    #    actor = json.dumps({"mbox":["mailto:me@example.com"]})
    #    response = self.client.get(reverse(views.actors), {'actor':actor})
    #    self.assertContains(response, 'mailto:me@example.com')
    #    self.assertContains(response, 'name')
    #    self.assertContains(response, 'me')
    
    def test_get_no_actor(self):
        response = self.client.get(reverse(views.actors), Authorization=self.auth, X_Experience_API_Version="0.95")
        self.assertEqual(response.status_code, 400)
    
    def test_post(self):
        actor = json.dumps({"name":["me"],"mbox":["mailto:me@example.com"]})
        response = self.client.post(reverse(views.actors), {'actor':actor},content_type='application/x-www-form-urlencoded', Authorization=self.auth, X_Experience_API_Version="0.95")
        self.assertEqual(response.status_code, 405)
