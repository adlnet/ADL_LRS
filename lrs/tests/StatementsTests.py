from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import views, models
from os import path
import sys
import json
import base64
from lrs.objects import Actor, Activity

class StatementsTests(TestCase):
    def setUp(self):
        self.username = "tester1"
        self.email = "test1@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {'username':self.username, 'email':self.email,'password':self.password,'password2':self.password}
        response = self.client.post(reverse(views.register),form)

    # def test_post_but_really_get(self):
    #     response = self.client.post(reverse(views.statements), {"verb":"created","object": {"id":"http://example.com/test_post_but_really_get"}},content_type='application/x-www-form-urlencoded', HTTP_AUTHORIZATION=self.auth)
    #     #print "\nTesting post with type to url form encoded\n %s \n-----done----" % response.content
    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, 'weird POST/GET')
        
    # def test_post_but_really_get_no_type(self):
    #     response = self.client.post(reverse(views.statements), {"verb":"created","object": {"id":"http://example.com/test_post_but_really_get_no_type"}}, HTTP_AUTHORIZATION=self.auth)
    #     #print "\nTesting post with no content type\n %s \n-----done----" % response.content
    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, 'weird POST/GET')
        
    def test_post_with_no_valid_params(self):
        # Error will be thrown in statements class
        self.assertRaises(Exception, self.client.post, reverse(views.statements), {"feet":"yes","hands": {"id":"http://example.com/test_post"}},content_type='application/json', HTTP_AUTHORIZATION=self.auth)

    def test_post(self):
        stmt = json.dumps({"verb":"created","object": {"id":"test_post"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        act = models.activity.objects.get(activity_id="test_post")
        actorName = models.agent_name.objects.get(name='tester1')
        actorMbox = models.agent_mbox.objects.get(mbox='test1@tester.com')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(act.activity_id, "test_post")
        
    def test_authority_stmt_field_post(self):
        stmt = json.dumps({"verb":"created","object": {"id":"test_post1"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        act = models.activity.objects.get(activity_id="test_post1")
        actorName = models.agent_name.objects.get(name='tester1')
        actorMbox = models.agent_mbox.objects.get(mbox='test1@tester.com')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(act.activity_id, "test_post1")

        self.assertEqual(actorName.name, 'tester1')
        self.assertEqual(actorMbox.mbox, 'test1@tester.com')

    # def test_get(self):
    #     stmt = json.dumps({"verb":"created","object": {"id":"test_get"}})
    #     post_response = self.client.post(reverse(views.statements), stmt, content_type="application/json", HTTP_AUTHORIZATION=self.auth)
    #     self.assertEqual(post_response.status_code, 200)

    #     response = self.client.get(reverse(views.statements), {'statementId': post_response.content})
    #     print response.__dict__



    def test_get_no_statementid(self):
        response = self.client.get(reverse(views.statements))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')
        self.assertContains(response, 'statementId parameter is missing')
