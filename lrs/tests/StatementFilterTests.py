from django.test import TestCase
# from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import views#, models
from lrs.models import statement
# from os import path
from django.conf import settings
# import sys
import json
import base64
import os.path
# import uuid
# from datetime import datetime, timedelta
# from django.utils.timezone import utc
# from lrs.objects import Activity, Statement
# import time
import urllib
# from lrs.util import retrieve_statement
# import pdb
# import hashlib
# import pprint

class StatementFilterTests(TestCase):

    def _pre_setup(self):
        print "presetup"
        root = os.path.dirname(os.path.realpath(__file__))
        loc = os.path.join(root, 'fmtdatadump.json')
        self.fixtures = [loc,]
        self.saved_stmt_limit=settings.SERVER_STMT_LIMIT
        settings.SERVER_STMT_LIMIT=100
        self.username = "tom"
        self.email = "tom@example.com"
        self.password = "1234"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        super(StatementFilterTests, self)._pre_setup()

    def _post_teardown(self):
        settings.SERVER_STMT_LIMIT=self.saved_stmt_limit
        super(StatementFilterTests, self)._post_teardown()
    
    def test_fixture(self):
        r = self.client.get(reverse(views.statements), X_Experience_API_Version="1.0", Authorization=self.auth)
        objs = json.loads(r.content)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(objs['statements']), len(statement.objects.all()))

    def test_limit_filter(self):
        # Test limit
        limitGetResponse = self.client.post(reverse(views.statements),{"limit":9}, content_type="application/x-www-form-urlencoded", X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(limitGetResponse.status_code, 200)
        rsp = limitGetResponse.content
        respList = json.loads(rsp)
        stmts = respList["statements"]
        self.assertEqual(len(stmts), 9)    

    def test_get_id(self):
        param = {"statementId":"da54afcd-08f2-4494-88e0-7ca9e5521d51"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        self.assertEqual(obj['result']['score']['raw'], 1918560)

    # def test_registration_filter(self):
    #     self.bunchostmts()
    #     # Test Registration
    #     param = {"registration": self.cguid4}
    #     path = "%s?%s" % (reverse(views.statements), urllib.urlencode(param))        
    #     registrationPostResponse = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)

    #     self.assertEqual(registrationPostResponse.status_code, 200)
    #     self.assertContains(registrationPostResponse,self.guid4)
    #     self.assertNotIn(self.guid2, registrationPostResponse)
    #     self.assertNotIn(self.guid3, registrationPostResponse)
    #     self.assertNotIn(self.guid1, registrationPostResponse)
    #     self.assertNotIn(self.guid5, registrationPostResponse)
    #     self.assertNotIn(self.guid6, registrationPostResponse)
    #     self.assertNotIn(self.guid7, registrationPostResponse)
    #     self.assertNotIn(self.guid8, registrationPostResponse)

    # def test_ascending_filter(self):
    #     self.bunchostmts()
    #     # Test actor
    #     ascending_get_response = self.client.get(reverse(views.statements), 
    #         {"ascending": True},content_type="application/x-www-form-urlencoded", X_Experience_API_Version="1.0", Authorization=self.auth)

    #     self.assertEqual(ascending_get_response.status_code, 200)
    #     rsp = ascending_get_response.content
    #     self.assertIn(self.guid1, rsp)
    #     self.assertIn(self.guid2, rsp)
    #     self.assertIn(self.guid3, rsp)
    #     self.assertIn(self.guid4, rsp)
    #     self.assertIn(self.guid5, rsp)
    #     self.assertIn(self.guid6, rsp)
    #     self.assertIn(self.guid7, rsp)
    #     self.assertIn(self.guid8, rsp)
    #     self.assertIn(str(self.exist_stmt_id), rsp)
    #     