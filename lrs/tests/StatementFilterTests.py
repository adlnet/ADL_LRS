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
import math
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
        sid = statement.objects.get(verb__verb_id="http://adlnet.gov/xapi/verbs/completed").statement_id
        param = {"statementId":sid}
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
        # get some time points for since and until
        for s in stmts:
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(statement.objects.get(statement_id=s['object']['id']).actor.get_agent_json()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))

        cnt_all = len(stmts)
        since = stmts[int(math.floor(len(stmts)/1.5))]['stored']
        until = stmts[int(math.ceil(len(stmts)/3))]['stored']
        since_cnt = int(math.floor(len(stmts)/1.5))
        until_cnt = cnt_all - int(math.ceil(len(stmts)/3))
        since_until_cnt = int(math.floor(len(stmts)/1.5)) - int(math.ceil(len(stmts)/3))
        
        param = {"agent":{"mbox":"mailto:tom@example.com"}, "since": since}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), since_cnt)
        since_ids=[]
        for s in stmts:
            since_ids.append(s['id'])
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(statement.objects.get(statement_id=s['object']['id']).actor.get_agent_json()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))

        param = {"agent":{"mbox":"mailto:tom@example.com"}, "until": until}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), until_cnt)
        until_ids=[]
        for s in stmts:
            until_ids.append(s['id'])
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(statement.objects.get(statement_id=s['object']['id']).actor.get_agent_json()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))
        same = [x for x in since_ids if x in until_ids]
        self.assertEqual(len(same), since_until_cnt)

        param = {"agent":{"mbox":"mailto:tom@example.com"}, "since": since, "until": until}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertTrue(len(stmts) < cnt_all)
        self.assertEqual(len(stmts), since_until_cnt)
        slice_ids=[]
        for s in stmts:
            slice_ids.append(s['id'])
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(statement.objects.get(statement_id=s['object']['id']).actor.get_agent_json()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))
        self.assertItemsEqual(slice_ids, same)

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
        since = stmts[int(math.floor(cnt_all/2))]['stored']
        since_cnt = int(math.floor(cnt_all/2))

        param = {"agent":{"mbox":"mailto:louo@example.com"}, "related_agents": True, "since": since}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), since_cnt)
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

        self.assertTrue(len(stmts) > actcnt, "stmts(%s) was not greater than actcnt(%s)" % (len(stmts), actcnt))

    def test_no_activity_filter(self):
        actorGetResponse = self.client.post(reverse(views.statements), 
            {"activity":"http://notarealactivity.com"},
             content_type="application/x-www-form-urlencoded", X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(actorGetResponse.status_code, 200)
        rsp = json.loads(actorGetResponse.content)
        stmts = rsp['statements']
        self.assertEqual(len(stmts), 0)

    def test_format_agent_filter(self):
        stmt = json.dumps({"actor":{"name":"lou wolford", "mbox":"mailto:louwolford@example.com"},
                          "verb":{"id":"http://special.adlnet.gov/xapi/verb/created",
                                  "display":{"en-US":"made"}},
                          "object":{"objectType":"Group","name":"androids","mbox":"mailto:androids@example.com",
                                    "member":[{"name":"Adam Link", "mbox":"mailto:alink@example.com"},
                                              {"name":"Andrew Martin", "mbox":"mailto:amartin@example.com"},
                                              {"name":"Astro Boy", "mbox":"mailto:astroboy@example.com"},
                                              {"name":"C-3PO", "mbox":"mailto:c3po@example.com"},
                                              {"name":"R2 D2", "mbox":"mailto:r2d2@example.com"},
                                              {"name":"Marvin", "mbox":"mailto:marvin@example.com"},
                                              {"name":"Data", "mbox":"mailto:data@example.com"},
                                              {"name":"Mr. Roboto", "mbox":"mailto:mrroboto@example.com"}
                                             ]
                                   },
                          "context":{"instructor":{"name":"Isaac Asimov", "mbox":"mailto:asimov@example.com"},
                                     "team":{"objectType":"Group", "name":"team kick***", 
                                             "member":[{"name":"lou wolford","mbox":"mailto:louwolford@example.com"},
                                                       {"name":"tom creighton", "mbox":"mailto:tomcreighton@example.com"}
                                                      ]
                                             }
                                     }
                         })
        guid = str(uuid.uuid1())
        param = {"statementId":guid}
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode(param))
        resp = self.client.put(path, stmt, content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(resp.status_code, 204)
        
        agent_params = ['name', 'mbox', 'objectType']

        param = {"agent":{"mbox":"mailto:louwolford@example.com"}}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        # only expecting the one made at the beginning of this test
        stmt_r = stmts[0]
        # remove the stuff the LRS adds
        stmt_r.pop('stored')
        stmt_r.pop('timestamp')
        stmt_r.pop('version')
        stmt_r.pop('id')
        stmt_r.pop('authority')
        orig_stmt = json.loads(stmt)

        self.assertItemsEqual(orig_stmt.keys(), stmt_r.keys())
        self.assertItemsEqual(agent_params, stmt_r['actor'].keys())
        self.assertItemsEqual(orig_stmt['object'].keys(), stmt_r['object'].keys())
        for m in stmt_r['object']['member']:
            self.assertItemsEqual(m.keys(), agent_params)
        self.assertItemsEqual(orig_stmt['context'].keys(), stmt_r['context'].keys())
        self.assertItemsEqual(agent_params, stmt_r['context']['instructor'].keys())
        self.assertItemsEqual(orig_stmt['context']['team'].keys(), stmt_r['context']['team'].keys())
        for m in stmt_r['context']['team']['member']:
            self.assertItemsEqual(m.keys(), agent_params)

        param = {"agent":{"mbox":"mailto:louwolford@example.com"}, "format":"ids"}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']

        agent_id_param = ['mbox']
        group_id_params = ['objectType', "mbox"]
        anon_id_params = ['objectType', "member"]

        # only expecting the one made at the beginning of this test
        stmt_r = stmts[0]
        # remove the stuff the LRS adds
        stmt_r.pop('stored')
        stmt_r.pop('timestamp')
        stmt_r.pop('version')
        stmt_r.pop('id')
        stmt_r.pop('authority')
        orig_stmt = json.loads(stmt)

        self.assertItemsEqual(orig_stmt.keys(), stmt_r.keys())
        self.assertItemsEqual(agent_id_param, stmt_r['actor'].keys())
        self.assertItemsEqual(group_id_params, stmt_r['object'].keys())
        self.assertItemsEqual(orig_stmt['context'].keys(), stmt_r['context'].keys())
        self.assertItemsEqual(agent_id_param, stmt_r['context']['instructor'].keys())
        self.assertItemsEqual(anon_id_params, stmt_r['context']['team'].keys())
        for m in stmt_r['context']['team']['member']:
            self.assertItemsEqual(m.keys(), agent_id_param)

    def test_agent_account(self):
        account = {"homePage":"http://www.adlnet.gov","name":"freakshow"}
        stmt = json.dumps({"actor": {"name": "freakshow", "account":account},
                           "verb":{"id":"http://tom.com/tested"},
                           "object":{"id":"http://tom.com/accountid"}})

        guid = str(uuid.uuid1())
        param = {"statementId":guid}
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode(param))
        resp = self.client.put(path, stmt, content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(resp.status_code, 204)

        param = {"agent":{"account":account}}
        path = "%s?%s" % (reverse(views.statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        ss = obj['statements']
        self.assertEqual(len(ss), 1)
        s = ss[0]
        self.assertEqual(s['id'], guid)
        self.assertEqual(s['actor']['account']['name'], account['name'])
        self.assertEqual(s['actor']['account']['homePage'], account['homePage'])

        
    
    # def test_activity_format(self):


