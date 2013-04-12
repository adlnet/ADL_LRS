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
from lrs.util import convert_to_utc
# import pdb
# import hashlib
# import pprint

class StatementFilterTests(TestCase):

    def _pre_setup(self):
        root = os.path.dirname(os.path.realpath(__file__))
        loc = os.path.join(root, 'ddfmt.json')
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

    def test_agent_filter(self):
        param = {"agent":{"mbox":"mailto:tom@example.com"}}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        for s in stmts:
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(statement.objects.get(statement_id=s['object']['id']).actor.get_agent_json()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))

    def test_group_as_agent_filter(self):
        param = {"agent":{"mbox":"mailto:adllrsdevs@example.com"}}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        count = len(statement.objects.filter(actor__mbox=param['agent']['mbox']))
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), count)
        for s in stmts:
            self.assertEqual(s['actor']['mbox'], param['agent']['mbox'])

    def test_related_agents_filter(self):
        param = {"agent":{"mbox":"mailto:louo@example.com"}}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 1)

        param = {"agent":{"mbox":"mailto:louo@example.com"}, "related_agents":True}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 6)

    def test_agent_filter_since_and_until(self):
        param = {"agent":{"mbox":"mailto:tom@example.com"}}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        for s in stmts:
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(statement.objects.get(statement_id=s['object']['id']).actor.get_agent_json()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))

        cnt_all = len(stmts)

        param = {"agent":{"mbox":"mailto:tom@example.com"}, "since": "2013-04-09T00:00Z"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertTrue(len(stmts) < cnt_all)
        since_ids=[]
        for s in stmts:
            since_ids.append(s['id'])
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(statement.objects.get(statement_id=s['object']['id']).actor.get_agent_json()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))

        param = {"agent":{"mbox":"mailto:tom@example.com"}, "until": "2013-04-09T00:00Z"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertTrue(len(stmts) < cnt_all)
        until_ids=[]
        for s in stmts:
            until_ids.append(s['id'])
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(statement.objects.get(statement_id=s['object']['id']).actor.get_agent_json()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))
        self.assertFalse(any((True for x in since_ids if x in until_ids)))

        param = {"agent":{"mbox":"mailto:tom@example.com"}, "since": "2013-04-09T00:00Z", "until": "2013-04-11T00:00Z"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertTrue(len(stmts) < cnt_all)
        self.assertTrue(len(stmts) < len(since_ids))
        slice_ids=[]
        for s in stmts:
            slice_ids.append(s['id'])
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(statement.objects.get(statement_id=s['object']['id']).actor.get_agent_json()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))
        self.assertTrue(any((True for x in slice_ids if x in since_ids)))
        self.assertFalse(any((True for x in slice_ids if x in until_ids)))

    def test_related_agents_filter_until(self):
        param = {"agent":{"mbox":"mailto:louo@example.com"}, "related_agents":True}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        for s in stmts:
            if param['agent']['mbox'] not in str(s['actor']):
                if s['object']['objectType'] != "StatementRef":
                    self.assertTrue(param['agent']['mbox'] in str(s))
                else:
                    self.assertEqual(s['object']['objectType'], "StatementRef")
                    refd = statement.objects.get(statement_id=s['object']['id']).object_return()
                    self.assertTrue(param['agent']['mbox'] in str(refd))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))

        cnt_all = len(stmts)

        param = {"agent":{"mbox":"mailto:louo@example.com"}, "related_agents": True, "until": "2013-04-10T00:00Z"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertTrue(len(stmts) < cnt_all)
        for s in stmts:
            if param['agent']['mbox'] not in str(s['actor']):
                if s['object']['objectType'] != "StatementRef":
                    self.assertTrue(param['agent']['mbox'] in str(s))
                else:
                    self.assertEqual(s['object']['objectType'], "StatementRef")
                    refd = statement.objects.get(statement_id=s['object']['id']).object_return()
                    self.assertTrue(param['agent']['mbox'] in str(refd))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))
            self.assertTrue(convert_to_utc(s['stored']) < convert_to_utc(param['until']))
