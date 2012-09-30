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

        self.guid1 = str(uuid.uuid4())
        self.guid2 = str(uuid.uuid4())
        self.guid3 = str(uuid.uuid4())    
        self.guid4 = str(uuid.uuid4())
        self.guid5 = str(uuid.uuid4())
        self.guid6 = str(uuid.uuid4())
        self.guid7 = str(uuid.uuid4())
        self.guid8 = str(uuid.uuid4())        
        self.cguid1 = str(uuid.uuid4())
        self.cguid2 = str(uuid.uuid4())    
        self.cguid3 = str(uuid.uuid4())
        self.cguid4 = str(uuid.uuid4())
        self.cguid5 = str(uuid.uuid4())

        self.existStmt = Statement.Statement(json.dumps({"verb":"created", "object": {"id":"activity"}}))

        self.mytime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())

        self.existStmt1 = json.dumps({"statement_id":self.guid1,"verb":"attempted", "object": {'objectType': 'Activity', 'id':'foogie',
            'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answer'],
            'extensions': {'key1': 'value1', 'key2': 'value2','key3': 'value3'}}}, 
            "result": {'score':{'scaled':.85}, 'completion': True, 'success': True, 'response': 'kicked',
            'duration': self.mytime, 'extensions':{'key1': 'value1', 'key2':'value2'}},
            'context':{'registration': self.cguid1, 'contextActivities': {'other': {'id': 'NewActivityID2'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey1': 'cval1',
            'ckey2': 'cval2'}}, 'authority':{'objectType':'Agent','name':['auth'],'mbox':['auth@example.com']}})        

        self.existStmt2 = json.dumps({"statement_id":self.guid2,"verb":"created", "object": {'objectType': 'Activity', 'id':'foogie',
            'definition': {'name': 'testname3','description': 'testdesc3', 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key11': 'value11', 'key22': 'value22','key33': 'value33'}}}, 
            "result": {'score':{'scaled':.75}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid2, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey11': 'cval11',
            'ckey22': 'cval22'}}, 'authority':{'objectType':'Agent','name':['auth2'],'mbox':['auth2@example.com']}})        

        self.existStmt3 = json.dumps({"statement_id":self.guid3,"verb":"created", "object": {'objectType': 'Activity', 'id':'foogals',
            'definition': {'name': 'testname3','description': 'testdesc3', 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
            "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid3, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
            'revision': 'food', 'platform':'bard','language': 'en-US','instructor':{'objectType': 'Agent', 'name':['bob'], 'mbox':['bob@bob.com'], 'account':[{'accountServiceHomePage':'http://example.com','accountName':'bobacct'}], 'openid':['bobopenid']}, 
            'extensions':{'ckey111': 'cval111','ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})        

        self.existStmt4 = json.dumps({"statement_id":self.guid4,
            "verb":"passed", "object": {'objectType': 'Activity', 'id':'foogal',
            'definition': {'name': 'testname3','description': 'testdesc3', 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
            "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid4, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
            'revision': 'food', 'platform':'bard','language': 'en-US','instructor':{'name':['bill'], 'mbox':['bill@bill.com'],'givenName':['william'], 'familyName':['smith'],
            'firstName':['billy'], 'lastName':['smith']},'extensions':{'ckey111': 'cval111','ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})

        self.existStmt5 = json.dumps({"statement_id":self.guid5, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})

        self.existStmt6 = json.dumps({"statement_id":self.guid6,"actor": {'objectType':'Person','name':['max'],'mbox':['max@max.com'],'givenName':['maximus'],
            'familyName':['zeus'], 'firstName':['maximus'], 'lastName':['zeus']}, "object":{'id': 'test_activity'},"verb":"talked"})

        self.existStmt7 = json.dumps({"statement_id":self.guid7,'object': {'objectType':'Person','name':['max'],'mbox':['max@max.com'],'givenName':['maximus'],
            'familyName':['amillion'], 'firstName':['max'], 'lastName':['amillion']}, 'verb': 'watched'})

        self.existStmt8 = json.dumps({"statement_id":self.guid8,'object': {'objectType':'Agent','name':['john'],'mbox':['john@john.com'],'account':[{'accountServiceHomePage':'http://john.com','accountName':'johnacct'}],
            'openid':['johnopenid']}, 'verb': 'watched'})

        # Post statements
        self.postresponse1 = self.client.post(reverse(views.statements), self.existStmt1,  content_type="application/json", Authorization=self.auth)
        time.sleep(1)

        self.postresponse3 = self.client.post(reverse(views.statements), self.existStmt3,  content_type="application/json", Authorization=self.auth)
        self.postresponse4 = self.client.post(reverse(views.statements), self.existStmt4,  content_type="application/json", Authorization=self.auth)
        
        self.secondTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())
        time.sleep(2)

        self.postresponse2 = self.client.post(reverse(views.statements), self.existStmt2,  content_type="application/json", Authorization=self.auth)
        self.postresponse5 = self.client.post(reverse(views.statements), self.existStmt5,  content_type="application/json", Authorization=self.auth)
        self.postresponse6 = self.client.post(reverse(views.statements), self.existStmt6,  content_type="application/json", Authorization=self.auth)
        self.postresponse7 = self.client.post(reverse(views.statements), self.existStmt7,  content_type="application/json", Authorization=self.auth)
        self.postresponse8 = self.client.post(reverse(views.statements), self.existStmt8,  content_type="application/json", Authorization=self.auth)
        

    def test_post_with_no_valid_params(self):
        # Error will be thrown in statements class
        resp = self.client.post(reverse(views.statements), {"feet":"yes","hands": {"id":"http://example.com/test_post"}},content_type='application/json', Authorization=self.auth)
        self.assertEqual(resp.status_code, 400)

    def test_post(self):
        stmt = json.dumps({"verb":"created","object": {"id":"test_post"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json", Authorization=self.auth)
        act = models.activity.objects.get(activity_id="test_post")
        actorName = models.agent_name.objects.get(name='tester1')
        actorMbox = models.agent_mbox.objects.get(mbox='test1@tester.com')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(act.activity_id, "test_post")

    def test_post_with_actor(self):
        stmt = json.dumps({"actor":{"mbox":["mailto:mr.t@example.com"]},"verb":"created","object": {"id":"i.pity.the.fool"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json", Authorization=self.auth)
        self.assertEqual(response.status_code, 200)
        models.agent_mbox.objects.get(mbox='mailto:mr.t@example.com')
    
    def test_list_post(self):
        stmts = json.dumps([{"verb":"created","object": {"id":"test_list_post"}},{"verb":"managed","object": {"id":"test_list_post1"}}])
        response = self.client.post(reverse(views.statements), stmts,  content_type="application/json", Authorization=self.auth)
        activity1 = models.activity.objects.get(activity_id="test_list_post")
        activity2 = models.activity.objects.get(activity_id="test_list_post1")
        stmt1 = models.statement.objects.get(stmt_object=activity1)
        stmt2 = models.statement.objects.get(stmt_object=activity2)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(stmt1.verb, "created")
        self.assertEqual(stmt2.verb, "managed")

    def test_authority_stmt_field_post(self):
        stmt = json.dumps({"verb":"created","object": {"id":"test_post1"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json", Authorization=self.auth)
        
        act = models.activity.objects.get(activity_id="test_post1")
        actorName = models.agent_name.objects.get(name='tester1')
        actorMbox = models.agent_mbox.objects.get(mbox='test1@tester.com')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(act.activity_id, "test_post1")

        self.assertEqual(actorName.name, 'tester1')
        self.assertEqual(actorMbox.mbox, 'test1@tester.com')

    def test_put(self):
        stmt = json.dumps({"statementId": "putID","verb":"created","object": {"id":"test_put"}})
        response = self.client.put(reverse(views.statements), stmt, content_type="application/json", Authorization=self.auth)
        act = models.activity.objects.get(activity_id="test_put")
        actorName = models.agent_name.objects.get(name='tester1')
        actorMbox = models.agent_mbox.objects.get(mbox='test1@tester.com')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(act.activity_id, "test_put")

    def test_no_content_put(self):
        stmt = json.dumps({"statementId": "putID"})
        response = self.client.put(reverse(views.statements), stmt, content_type="application/json", Authorization=self.auth)

        self.assertEqual(response.status_code, 204)

    def test_existing_stmtID_put(self):
        existStmt = Statement.Statement(json.dumps({"statement_id":"blahID","verb":"created", "object": {"id":"activity"}}))
        stmt = json.dumps({"statementId": "blahID","verb":"created","object": {"id":"test_put"}})
        response = self.client.put(reverse(views.statements), stmt, content_type="application/json", Authorization=self.auth)
        
        self.assertEqual(response.status_code, 409)        

    def test_missing_stmtID_put(self):        
        stmt = json.dumps({"verb":"created","object": {"id":"test_put"}})
        response = self.client.put(reverse(views.statements), stmt, content_type="application/json", Authorization=self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertIn(response.content, "Error -- statements - method = PUT, but statementId paramater is missing")

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
        # print response.content
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
        jsn = json.loads(response.content)
        self.assertEqual(len(jsn['statements']), models.statement.objects.all().count())
        # self.assertContains(response, 'Error')
        # self.assertContains(response, 'statementId parameter is missing')

        
    def test_since_filter(self):
        # Test since - should only get existStmt2-4 since existStmt is stored at same time as mytime
        sinceGetResponse = self.client.get(reverse(views.statements), {'since': self.mytime})
        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertContains(sinceGetResponse, self.postresponse2.content)
        self.assertContains(sinceGetResponse, self.postresponse3.content)
        self.assertContains(sinceGetResponse, self.postresponse4.content)
        self.assertContains(sinceGetResponse, self.postresponse5.content)
        self.assertNotIn(self.postresponse1.content, sinceGetResponse)


    def test_until_filter(self):
        # Test until
        untilGetResponse = self.client.post(reverse(views.statements), {'until': self.secondTime}, content_type="application/x-www-form-urlencoded")
        self.assertEqual(untilGetResponse.status_code, 200)
        self.assertContains(untilGetResponse, self.postresponse1.content)
        self.assertContains(untilGetResponse, self.postresponse3.content)
        self.assertContains(untilGetResponse, self.postresponse4.content)
        self.assertNotIn(self.postresponse2.content, untilGetResponse)
        self.assertNotIn(self.postresponse5.content, untilGetResponse)


    def test_activity_object_filter(self):
        # Test activity object
        activityObjectGetResponse = self.client.get(reverse(views.statements), {'object':{'objectType': 'Activity', 'id':'foogie'}})
        self.assertEqual(activityObjectGetResponse.status_code, 200)
        self.assertContains(activityObjectGetResponse, self.postresponse1.content)
        self.assertContains(activityObjectGetResponse, self.postresponse2.content)
        self.assertNotIn(self.postresponse3.content, activityObjectGetResponse)
        self.assertNotIn(self.postresponse4.content, activityObjectGetResponse)
        self.assertNotIn(self.postresponse5.content, activityObjectGetResponse)

    def test_no_actor(self):
        # Test actor object
        actorObjectGetResponse = self.client.get(reverse(views.statements), {"object":{"objectType": "person", 'mbox':['nobody@example.com']}})
        self.assertEqual(actorObjectGetResponse.status_code, 200)
        stmts = json.loads(actorObjectGetResponse.content)
        dbstmts = models.statement.objects.all()
        self.assertEqual(len(stmts['statements']), len(dbstmts))

    def test_actor_object_filter(self):
        # Test actor object
        actorObjectGetResponse = self.client.get(reverse(views.statements), {"object":{"objectType": "person", 'name':['jon'],'mbox':['jon@jon.com']}})
        self.assertEqual(actorObjectGetResponse.status_code, 200)
        self.assertContains(actorObjectGetResponse, self.postresponse5.content)
        self.assertNotIn(self.postresponse4.content, actorObjectGetResponse)
        self.assertNotIn(self.postresponse2.content, actorObjectGetResponse)
        self.assertNotIn(self.postresponse3.content, actorObjectGetResponse)
        self.assertNotIn(self.postresponse1.content, actorObjectGetResponse)


    def test_registration_filter(self):
        # Test Registration
        registrationGetResponse = self.client.post(reverse(views.statements), {'registration': self.cguid4}, content_type="application/x-www-form-urlencoded")
        self.assertEqual(registrationGetResponse.status_code, 200)
        self.assertContains(registrationGetResponse,self.postresponse4.content)
        self.assertNotIn(self.postresponse2.content, registrationGetResponse)
        self.assertNotIn(self.postresponse3.content, registrationGetResponse)
        self.assertNotIn(self.postresponse1.content, registrationGetResponse)
        self.assertNotIn(self.postresponse5.content, registrationGetResponse)


    def test_actor_filter(self):
        # Test actor
        actorGetResponse = self.client.post(reverse(views.statements), {'actor':{"objectType": "person", 'name':['tester1'],'mbox':['test1@tester.com']}}, content_type="application/x-www-form-urlencoded")
        self.assertEqual(actorGetResponse.status_code, 200)
        self.assertContains(actorGetResponse,self.postresponse1.content)
        self.assertContains(actorGetResponse,self.postresponse2.content)
        self.assertContains(actorGetResponse,self.postresponse3.content)                
        self.assertNotIn(self.postresponse4.content, actorGetResponse)
        self.assertNotIn(self.postresponse5.content, actorGetResponse)


    def test_instructor_filter(self):
        # Test instructor - will only return one b/c actor in stmt supercedes instructor in context
        instructorGetResponse = self.client.post(reverse(views.statements), {"instructor":{"name":["bill"],"mbox":["bill@bill.com"]}},  content_type="application/x-www-form-urlencoded")
        self.assertEqual(instructorGetResponse.status_code, 200)
        self.assertContains(instructorGetResponse, self.postresponse4.content)
        self.assertNotIn(self.postresponse2.content, instructorGetResponse)
        self.assertNotIn(self.postresponse3.content, instructorGetResponse)
        self.assertNotIn(self.postresponse1.content, instructorGetResponse)
        self.assertNotIn(self.postresponse5.content, instructorGetResponse)

    def test_authoritative_filter(self):
        # Test authoritative
        self.username = "tester1"
        self.email = "test1@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {'username':self.username, 'email':self.email,'password':self.password,'password2':self.password}
        response = self.client.post(reverse(views.register),form)
        raw_stmt = {"actor":{"name":["tom"],"mbox":["mailto:tom@example.com"]},
                    "verb":"attempted",
                    "object":{"id":"http://adlnet.gov/object.1"},
                    "context":{"registration": str(uuid.uuid4), "contextActivities": {"other": {"id": "NewActivityID2"}}},
                    "authority":{"name":["auth"],"mbox":["mailto:auth@example.com"]}}
        stmt = json.dumps(raw_stmt)
        #stmt1_resp = self.client.post(reverse(views.statements), stmt, content_type="application/json", Authorization=self.auth)
        stmt1_resp = self.client.get(reverse(views.statements), raw_stmt)
        self.assertEqual(stmt1_resp.status_code, 200)
        stmts = json.loads(stmt1_resp.content)
        self.assertEqual(len(stmts['statements']), 1)

    def test_limit_filter(self):
        # Test limit
        limitGetResponse = self.client.post(reverse(views.statements),{'limit':1}, content_type="application/x-www-form-urlencoded")
        respList = json.loads(limitGetResponse.content)
        stmts = respList['statements']
        self.assertEqual(len(stmts), 1)


    def test_sparse_filter(self):
        # Test sparse
        sparseGetResponse = self.client.post(reverse(views.statements),{'sparse': False}, content_type="application/x-www-form-urlencoded")
        self.assertEqual(sparseGetResponse.status_code, 200)
        self.assertContains(sparseGetResponse, 'activity_definition')        
        self.assertContains(sparseGetResponse, 'firstName')
        self.assertContains(sparseGetResponse, 'lastName')
        self.assertContains(sparseGetResponse, 'givenName')
        self.assertContains(sparseGetResponse, 'familyName')
        self.assertContains(sparseGetResponse, 'account')
        self.assertContains(sparseGetResponse, 'openid')



    def test_linked_filters(self):
        # Test reasonable linked query
        linkedGetResponse = self.client.get(reverse(views.statements), {'verb':'created', 'object':{'objectType': 'Activity', 'id':'foogie'}, 'since':self.secondTime, 'authoritative':'False', 'sparse': False})
        self.assertEqual(linkedGetResponse.status_code, 200)
        self.assertContains(linkedGetResponse, self.postresponse2.content)
