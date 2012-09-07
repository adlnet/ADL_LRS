from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import views, models
from os import path
import sys
import json
import base64
import uuid
from datetime import datetime
from django.utils.timezone import utc
from lrs.objects import Actor, Activity, Statement
import time

class StatementsTests(TestCase):
    def setUp(self):
        self.username = "tester1"
        self.email = "test1@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {'username':self.username, 'email':self.email,'password':self.password,'password2':self.password}
        response = self.client.post(reverse(views.register),form)
        
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
    
    # Only time posting form data will be when using POST for GET
    # def test_form_post(self):
    #     stmt = {"verb": "tested", "object": {"id":"test_form_post"}}
    #     response = self.client.post(reverse(views.statements), stmt, content_type="application/x-www-form-urlencoded", HTTP_AUTHORIZATION=self.auth)
    #     act = models.activity.objects.get(activity_id="test_form_post")
    #     actorName = models.agent_name.objects.get(name='tester1')
    #     actorMbox = models.agent_mbox.objects.get(mbox='test1@tester.com')

    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(act.activity_id, "test_form_post")        

    def test_list_post(self):
        stmts = json.dumps([{"verb":"created","object": {"id":"test_list_post"}},{"verb":"managed","object": {"id":"test_list_post1"}}])
        response = self.client.post(reverse(views.statements), stmts,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        activity1 = models.activity.objects.get(activity_id="test_list_post")
        activity2 = models.activity.objects.get(activity_id="test_list_post1")
        stmt1 = models.statement.objects.get(stmt_object=activity1)
        stmt2 = models.statement.objects.get(stmt_object=activity2)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(stmt1.verb, "created")
        self.assertEqual(stmt2.verb, "managed")

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

    def test_put(self):
        stmt = json.dumps({"statementId": "putID","verb":"created","object": {"id":"test_put"}})
        response = self.client.put(reverse(views.statements), stmt, content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        act = models.activity.objects.get(activity_id="test_put")
        actorName = models.agent_name.objects.get(name='tester1')
        actorMbox = models.agent_mbox.objects.get(mbox='test1@tester.com')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(act.activity_id, "test_put")

    def test_existing_stmtID_put(self):
        existStmt = Statement.Statement(json.dumps({"statement_id":"blahID","verb":"created", "object": {"id":"activity"}}))
        stmt = json.dumps({"statementId": "blahID","verb":"created","object": {"id":"test_put"}})
        response = self.client.put(reverse(views.statements), stmt, content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        
        self.assertEqual(response.status_code, 204)        

    def test_missing_stmtID_put(self):        
        stmt = json.dumps({"verb":"created","object": {"id":"test_put"}})
        response = self.client.put(reverse(views.statements), stmt, content_type="application/json", HTTP_AUTHORIZATION=self.auth)

        self.assertContains(response, "Error -- statements - method = PUT, but statementId paramater is missing")

    def test_get(self):
        guid = str(uuid.uuid4())
        cguid = str(uuid.uuid4())
        time = str(datetime.now())                
        bob = Actor.Actor(json.dumps({'objectType':'Person','name':['bob'],'mbox':['bob@example.com']}),create=True)
        existStmt = Statement.Statement(json.dumps({"statement_id":guid, "actor":{'objectType':'Person','name':['jon1'],'mbox':['jon1@example.com']} ,
            "verb":"created", "object": {'objectType': 'Activity', 'id':'foog',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'fill-in','correctResponsesPattern': ['Fill in answer'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}, "result": {'score':{'scaled':.95}, 'completion': True, 'success': True, 'response': 'kicked', 'duration': time, 'extensions':{'key1': 'value1', 'key2':'value2'}},
            'context':{'registration': cguid, 'contextActivities': {'other': {'id': 'NewActivityID'}}, 'revision': 'foo', 'platform':'bar',
                'language': 'en-US', 'extensions':{'ckey1': 'cval1', 'ckey2': 'cval2'}}, 'authority':{'objectType':'Agent','name':['auth'],'mbox':['auth@example.com']}}))        
        

        response = self.client.get(reverse(views.statements), {'statementId': guid})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'jon')
        self.assertContains(response, 'created')
        self.assertContains(response, 'foog')
        self.assertContains(response, 'testname2')
        self.assertContains(response, 'Fill in answer')
        self.assertContains(response, 'key1')
        self.assertContains(response, .95)
        self.assertContains(response, 'NewActivityID')
        self.assertContains(response, 'kicked')
        self.assertContains(response, 'bar')
        self.assertContains(response, 'ckey')
        self.assertContains(response, 'auth')

    def test_get_no_statementid(self):
        response = self.client.get(reverse(views.statements))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')
        self.assertContains(response, 'statementId parameter is missing')

    def test_post_but_really_get(self):
        guid1 = str(uuid.uuid4())
        guid2 = str(uuid.uuid4())
        guid3 = str(uuid.uuid4())    
        guid4 = str(uuid.uuid4())
        cguid1 = str(uuid.uuid4())
        cguid2 = str(uuid.uuid4())    
        cguid3 = str(uuid.uuid4())
        cguid4 = str(uuid.uuid4())    
        mytime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())

        importStmt1 = json.dumps({'verb': 'imported', 'object':{'objectType': 'Activity', 'id': 'foogie'}})
        importStmt2 = json.dumps({'verb': 'imported', 'object':{'objectType': 'Activity', 'id': 'foogals'}})
        importStmt3 = json.dumps({'verb': 'imported', 'object':{'objectType': 'Activity', 'id': 'foogal'}})


        existStmt1 = json.dumps({"statement_id":guid1,"verb":"created", "object": {'objectType': 'Activity', 'id':'foogie',
            'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answer'],
            'extensions': {'key1': 'value1', 'key2': 'value2','key3': 'value3'}}}, 
            "result": {'score':{'scaled':.85}, 'completion': True, 'success': True, 'response': 'kicked',
            'duration': mytime, 'extensions':{'key1': 'value1', 'key2':'value2'}},
            'context':{'registration': cguid1, 'contextActivities': {'other': {'id': 'NewActivityID2'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey1': 'cval1',
            'ckey2': 'cval2'}}, 'authority':{'objectType':'Agent','name':['auth'],'mbox':['auth@example.com']}})        

        existStmt2 = json.dumps({"statement_id":guid2,"verb":"created", "object": {'objectType': 'Activity', 'id':'foogie',
            'definition': {'name': 'testname3','description': 'testdesc3', 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key11': 'value11', 'key22': 'value22','key33': 'value33'}}}, 
            "result": {'score':{'scaled':.75}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': cguid2, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey11': 'cval11',
            'ckey22': 'cval22'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})        

        existStmt3 = json.dumps({"statement_id":guid3,"verb":"created", "object": {'objectType': 'Activity', 'id':'foogals',
            'definition': {'name': 'testname3','description': 'testdesc3', 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
            "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': cguid3, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey111': 'cval111',
            'ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})        

        existStmt4 = json.dumps({"statement_id":guid4,"verb":"passed", "object": {'objectType': 'Activity', 'id':'foogal',
            'definition': {'name': 'testname3','description': 'testdesc3', 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
            "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': cguid4, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey111': 'cval111',
            'ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})


        importresponse1 = self.client.post(reverse(views.statements), importStmt1,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        # importresponse2 = self.client.post(reverse(views.statements), importStmt2,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        # importresponse3 = self.client.post(reverse(views.statements), importStmt3,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)

        postresponse1 = self.client.post(reverse(views.statements), existStmt1,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        # postresponse2 = self.client.post(reverse(views.statements), existStmt2,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        # time.sleep(4)
        # postresponse3 = self.client.post(reverse(views.statements), existStmt3,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        # postresponse4 = self.client.post(reverse(views.statements), existStmt4,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        

        # getresponse1 = self.client.get(reverse(views.statements), {'verb': 'passed','since': mytime})
        # print response4

        # secondTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())

        
        # getpostresponse1 = self.client.post(reverse(views.statements), {'verb': 'created','until': secondTime})
        # print getpostresponse1

        getresponse2 = self.client.get(reverse(views.statements), {'verb': 'created','since': mytime,'object':{'objectType': 'Activity', 'id':'foogie'}})
        print getresponse2













