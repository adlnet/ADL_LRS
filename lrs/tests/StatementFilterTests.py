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
import uuid
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
        until = convert_to_utc(param['until'])
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
            self.assertTrue(convert_to_utc(s['stored']) < until)

    def test_related_agents_filter_since(self):
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

        param = {"agent":{"mbox":"mailto:louo@example.com"}, "related_agents": True, "since": "2013-04-10T00:00Z"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertTrue(len(stmts) < cnt_all)
        since = convert_to_utc(param['since'])
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
            self.assertTrue(convert_to_utc(s['stored']) > since)


    def test_since_filter_tz(self):
        stmt1_guid = str(uuid.uuid1())
        stmt1 = json.dumps({"verb":{"id": "http://adlnet.gov/expapi/verbs/created",
                "display": {"en-US":"created"}}, "object": {"id":"act:activity"},
                "actor":{"objectType":"Agent","mbox":"mailto:s@s.com"}, "timestamp":"2013-02-02T12:00:00-05:00"})

        param = {"statementId":stmt1_guid}
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode(param))
        stmt_payload = stmt1
        resp = self.client.put(path, stmt_payload, content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(resp.status_code, 204)
        time = "2013-02-02T12:00:32-05:00"
        stmt = statement.objects.filter(statement_id=stmt1_guid).update(stored=time)

        stmt2_guid = str(uuid.uuid1())
        stmt2 = json.dumps({"verb":{"id": "http://adlnet.gov/expapi/verbs/created",
                "display": {"en-US":"created"}}, "object": {"id":"act:activity2"},
                "actor":{"objectType":"Agent","mbox":"mailto:s@s.com"}, "timestamp":"2013-02-02T20:00:00+05:00"})

        param = {"statementId":stmt2_guid}
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode(param))
        stmt_payload = stmt2
        resp = self.client.put(path, stmt_payload, content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(resp.status_code, 204)
        time = "2013-02-02T10:00:32-05:00"
        stmt = statement.objects.filter(statement_id=stmt2_guid).update(stored=time)

        param = {"since": "2013-02-02T14:00Z"}
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode(param))      
        sinceGetResponse = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)

        self.assertEqual(sinceGetResponse.status_code, 200)
        rsp = sinceGetResponse.content
        self.assertIn(stmt1_guid, rsp)
        self.assertIn(stmt2_guid, rsp)

        param2 = {"since": "2013-02-02T16:00Z"}
        path2 = "%s?%s" % (reverse(views.statements), urllib.urlencode(param2))      
        sinceGetResponse2 = self.client.get(path2, X_Experience_API_Version="1.0", Authorization=self.auth)

        self.assertEqual(sinceGetResponse2.status_code, 200)
        rsp2 = sinceGetResponse2.content
        self.assertIn(stmt1_guid, rsp2)
        self.assertNotIn(stmt2_guid, rsp2)

    def test_verb_filter(self):
        param = {"verb":"http://special.adlnet.gov/xapi/verbs/high-fived"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 2)

        stmt_ref_stmt_ids = [k['object']['id'] for k in stmts if k['object']['objectType']=='StatementRef']
        stmt_ids = [k['id'] for k in stmts if k['object']['objectType']!='StatementRef']
        diffs = set(stmt_ref_stmt_ids) ^ set(stmt_ids)
        self.assertFalse(diffs)

        param = {"agent":{"mbox":"mailto:drdre@example.com"},"verb":"http://special.adlnet.gov/xapi/verbs/high-fived"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 0)

    def test_registration_filter(self):
        param = {"registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 20)

        param = {"registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91","verb":"http://special.adlnet.gov/xapi/verbs/high-fived"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 0)

        param = {"registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91","verb":"http://adlnet.gov/xapi/verbs/completed"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 1)

        param = {"agent":{"mbox":"mailto:tom@example.com"}, "registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91","verb":"http://adlnet.gov/xapi/verbs/completed"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 1)

        param = {"agent":{"mbox":"mailto:louo@example.com"}, "registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91","verb":"http://adlnet.gov/xapi/verbs/completed"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 0)

    def test_activity_filter(self):
        param = {"activity":"act:adlnet.gov/JsTetris_TCAPI"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        for s in stmts:
            if param['activity'] not in str(s['object']['id']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['activity'] in str(statement.objects.get(statement_id=s['object']['id']).object_return()))
            else:
                self.assertEqual(s['object']['id'], param['activity'])

        actcnt = len(stmts)
        self.assertEqual(actcnt, 4)

        param = {"activity":"act:adlnet.gov/JsTetris_TCAPI", "related_activities":True}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        for s in stmts:
            if param['activity'] not in str(s):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['activity'] in str(statement.objects.get(statement_id=s['object']['id']).object_return()))
            else:
                self.assertIn(param['activity'], str(s))

        self.assertTrue(len(stmts) > actcnt)

    def test_format_filter(self):
        param = {}
