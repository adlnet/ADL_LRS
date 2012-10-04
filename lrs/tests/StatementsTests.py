from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import views, models
from os import path
import sys
import json
import base64
import uuid
from datetime import datetime, timedelta
from django.utils.timezone import utc
from lrs.objects import Actor, Activity, Statement
import time
import urllib
from lrs.util import retrieve_statement
import pdb

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

        self.firstTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())

        self.existStmt1 = json.dumps({"verb":"attempted", "object": {'objectType': 'Activity', 'id':'foogie',
            'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'}, 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answer'],
            'extensions': {'key1': 'value1', 'key2': 'value2','key3': 'value3'}}}, 
            "result": {'score':{'scaled':.85}, 'completion': True, 'success': True, 'response': 'kicked',
            'duration': self.firstTime, 'extensions':{'key1': 'value1', 'key2':'value2'}},
            'context':{'registration': self.cguid1, 'contextActivities': {'other': {'id': 'NewActivityID2'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey1': 'cval1',
            'ckey2': 'cval2'}}, 'authority':{'objectType':'Agent','name':['auth'],'mbox':['auth@example.com']}})        

        self.existStmt2 = json.dumps({"verb":"created", "object": {'objectType': 'Activity', 'id':'foogie',
            'definition': {'name': {'en-US':'testname3'},'description': {'en-US':'testdesc3'}, 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key11': 'value11', 'key22': 'value22','key33': 'value33'}}}, 
            "result": {'score':{'scaled':.75}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.firstTime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid2, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey11': 'cval11',
            'ckey22': 'cval22'}}, 'authority':{'objectType':'Agent','name':['auth2'],'mbox':['auth2@example.com']}})        

        self.existStmt3 = json.dumps({"verb":"created", "object": {'objectType': 'Activity', 'id':'foogals',
            'definition': {'name': {'en-US':'testname3'},'description': {'en-US':'testdesc3'}, 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
            "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.firstTime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid3, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
            'revision': 'food', 'platform':'bard','language': 'en-US','instructor':{'objectType': 'Agent', 'name':['bob'], 'mbox':['bob@bob.com'], 'account':[{'accountServiceHomePage':'http://example.com','accountName':'bobacct'}], 'openid':['bobopenid']}, 
            'extensions':{'ckey111': 'cval111','ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})        

        self.existStmt4 = json.dumps({"verb":"passed", "object": {'objectType': 'Activity', 'id':'foogal',
            'definition': {'name': {'en-US':'testname3'},'description': {'en-US':'testdesc3'}, 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
            "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.firstTime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid4, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
            'revision': 'food', 'platform':'bard','language': 'en-US','instructor':{'name':['bill'], 'mbox':['bill@bill.com'],'givenName':['william'], 'familyName':['smith'],
            'firstName':['billy'], 'lastName':['smith']},'extensions':{'ckey111': 'cval111','ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})

        self.existStmt5 = json.dumps({"object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})

        self.existStmt6 = json.dumps({"actor": {'objectType':'Person','name':['max'],'mbox':['max@max.com'],'givenName':['maximus'],
            'familyName':['zeus'], 'firstName':['maximus'], 'lastName':['zeus']}, "object":{'id': 'test_activity'},"verb":"talked"})

        self.existStmt7 = json.dumps({'object': {'objectType':'Person','name':['max'],'mbox':['max@max.com'],'givenName':['maximus'],
            'familyName':['amillion'], 'firstName':['max'], 'lastName':['amillion']}, 'verb': 'watched'})

        self.existStmt8 = json.dumps({'object': {'objectType':'Agent','name':['john'],'mbox':['john@john.com'],'account':[{'accountServiceHomePage':'http://john.com','accountName':'johnacct'}],
            'openid':['johnopenid']}, 'verb': 'watched'})

        # Put statements
        param = {"statementId":self.guid1}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))
        stmt_payload = self.existStmt1
        self.putresponse1 = self.client.put(path, stmt_payload, content_type="application/json", Authorization=self.auth)
        self.assertEqual(self.putresponse1.status_code, 204)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=2)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid1).update(stored=time)


        param = {"statementId":self.guid3}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))
        stmt_payload = self.existStmt3
        self.putresponse3 = self.client.put(path, stmt_payload, content_type="application/json", Authorization=self.auth)
        self.assertEqual(self.putresponse3.status_code, 204)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=2)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid3).update(stored=time)

        
        param = {"statementId":self.guid4}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))
        stmt_payload = self.existStmt4
        self.putresponse4 = self.client.put(path, stmt_payload, content_type="application/json", Authorization=self.auth)
        self.assertEqual(self.putresponse4.status_code, 204)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=2)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid4).update(stored=time)

        self.secondTime = str((datetime.utcnow()+timedelta(seconds=4)).replace(tzinfo=utc).isoformat())
        
        param = {"statementId":self.guid2}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))
        stmt_payload = self.existStmt2
        self.putresponse2 = self.client.put(path, stmt_payload, content_type="application/json", Authorization=self.auth)       
        self.assertEqual(self.putresponse2.status_code, 204)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=6)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid2).update(stored=time)


        param = {"statementId":self.guid5}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))
        stmt_payload = self.existStmt5
        self.putresponse5 = self.client.put(path, stmt_payload, content_type="application/json", Authorization=self.auth)
        self.assertEqual(self.putresponse5.status_code, 204)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=6)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid5).update(stored=time)
        

        param = {"statementId":self.guid6}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))
        stmt_payload = self.existStmt6
        self.putresponse6 = self.client.put(path, stmt_payload, content_type="application/json", Authorization=self.auth)
        self.assertEqual(self.putresponse6.status_code, 204)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=6)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid6).update(stored=time)

        
        param = {"statementId":self.guid7}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))
        stmt_payload = self.existStmt7        
        self.putresponse7 = self.client.put(path, stmt_payload,  content_type="application/json", Authorization=self.auth)
        self.assertEqual(self.putresponse7.status_code, 204)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=6)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid7).update(stored=time)
        

        param = {"statementId":self.guid8}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))
        stmt_payload = self.existStmt8        
        self.putresponse8 = self.client.put(path, stmt_payload, content_type="application/json", Authorization=self.auth)
        self.assertEqual(self.putresponse8.status_code, 204)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=6)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid8).update(stored=time)
        

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
        guid = str(uuid.uuid4())

        param = {"statementId":guid}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))
        stmt = json.dumps({"verb":"created","object": {"id":"test_put"}})

        putResponse = self.client.put(path, stmt, content_type="application/json", Authorization=self.auth)

        act = models.activity.objects.get(activity_id="test_put")
        actorName = models.agent_name.objects.get(name='tester1')
        actorMbox = models.agent_mbox.objects.get(mbox='test1@tester.com')
        stmt = models.statement.objects.get(statement_id=guid)
        
        self.assertEqual(putResponse.status_code, 204)
        self.assertEqual(stmt.verb, 'created')
        self.assertEqual(act.activity_id, "test_put")

    def test_put_url_param(self):
        guid = str(uuid.uuid4())
        
        param = {"statementId":guid}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))
        stmt = {"verb":"created","object": {"id":"test_put"}}
        
        putResponse = self.client.put(path, stmt, content_type="application/json", Authorization=self.auth)
        self.assertEqual(putResponse.status_code, 204)

        stmt = models.statement.objects.get(statement_id=guid)
        self.assertEqual(stmt.verb, 'created')

    def test_no_content_put(self):
        guid = str(uuid.uuid4())
        
        param = {"statementId":guid}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))        
        stmt = json.dumps({})

        putResponse = self.client.put(path, stmt, content_type="application/json", Authorization=self.auth)

        self.assertEqual(putResponse.status_code, 204)

    def test_existing_stmtID_put(self):
        guid = str(uuid.uuid4())

        existStmt = Statement.Statement(json.dumps({"statement_id":guid,"verb":"created", "object": {"id":"activity"}}))

        param = {"statementId":guid}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))        
        stmt = json.dumps({"verb": "attached", "object":{"id":"test_existing_put"}})

        putResponse = self.client.put(path, stmt, content_type="application/json", Authorization=self.auth)
        
        self.assertEqual(putResponse.status_code, 409)        

    def test_missing_stmtID_put(self):        
        stmt = json.dumps({"verb":"created","object": {"id":"test_put"}})
        response = self.client.put(reverse(views.statements), stmt, content_type="application/json", Authorization=self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertIn(response.content, "Error -- statements - method = PUT, but statementId paramater is missing")

    def test_get(self):
        param = {"statementId":self.guid1}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))        
        getResponse = self.client.get(path)

        self.assertEqual(getResponse.status_code, 200)
        self.assertContains(getResponse, self.guid1)

    def test_get_no_statementid(self):
        getResponse = self.client.get(reverse(views.statements))
        self.assertEqual(getResponse.status_code, 200)
        jsn = json.loads(getResponse.content)
        self.assertEqual(len(jsn['statements']), models.statement.objects.all().count())
        # self.assertContains(response, 'Error')
        # self.assertContains(response, 'statementId parameter is missing')

        
    def test_since_filter(self):
        # Test since - should only get existStmt1-8 since existStmt is stored at same time as firstTime
        param = {'since': self.firstTime}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))        
        sinceGetResponse = self.client.get(path)
        # pdb.set_trace()

        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertContains(sinceGetResponse, self.guid1)
        self.assertContains(sinceGetResponse, self.guid2)
        self.assertContains(sinceGetResponse, self.guid3)
        self.assertContains(sinceGetResponse, self.guid4)
        self.assertContains(sinceGetResponse, self.guid5)
        self.assertContains(sinceGetResponse, self.guid6)
        self.assertContains(sinceGetResponse, self.guid7)
        self.assertContains(sinceGetResponse, self.guid8)

    def test_until_filter(self):
        # Test until
        param = {'until': self.secondTime}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))        
        untilGetResponse = self.client.get(path)
        
        # pdb.set_trace()
        self.assertEqual(untilGetResponse.status_code, 200)
        self.assertContains(untilGetResponse, self.guid1)
        self.assertContains(untilGetResponse, self.guid3)
        self.assertContains(untilGetResponse, self.guid4)
        self.assertNotIn(self.guid2, untilGetResponse)
        self.assertNotIn(self.guid5, untilGetResponse)
        self.assertNotIn(self.guid6, untilGetResponse)
        self.assertNotIn(self.guid7, untilGetResponse)
        self.assertNotIn(self.guid8, untilGetResponse)

    def test_activity_object_filter(self):
        # Test activity object
        param = {'object':{'objectType': 'Activity', 'id':'foogie'}}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))        
        activityObjectGetResponse = self.client.get(path)

        self.assertEqual(activityObjectGetResponse.status_code, 200)
        self.assertContains(activityObjectGetResponse, self.guid1)
        self.assertContains(activityObjectGetResponse, self.guid2)
        self.assertNotIn(self.guid3, activityObjectGetResponse)
        self.assertNotIn(self.guid4, activityObjectGetResponse)
        self.assertNotIn(self.guid5, activityObjectGetResponse)
        self.assertNotIn(self.guid6, activityObjectGetResponse)
        self.assertNotIn(self.guid7, activityObjectGetResponse)
        self.assertNotIn(self.guid8, activityObjectGetResponse)


    def test_no_actor(self):
        # Test actor object
        param = {"object":{"objectType": "person", 'mbox':['nobody@example.com']}}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))        
        actorObjectGetResponse = self.client.get(path)
        
        self.assertEqual(actorObjectGetResponse.status_code, 200)
        stmts = json.loads(actorObjectGetResponse.content)
        dbstmts = models.statement.objects.all()
        self.assertEqual(len(stmts['statements']), len(dbstmts))

    def test_actor_object_filter(self):
        # Test actor object
        param = {"object":{"objectType": "person", 'name':['jon'],'mbox':['jon@jon.com']}}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))        
        actorObjectGetResponse = self.client.get(path)
        
        self.assertEqual(actorObjectGetResponse.status_code, 200)
        self.assertContains(actorObjectGetResponse, self.guid5)
        self.assertNotIn(self.guid4, actorObjectGetResponse)
        self.assertNotIn(self.guid2, actorObjectGetResponse)
        self.assertNotIn(self.guid3, actorObjectGetResponse)
        self.assertNotIn(self.guid1, actorObjectGetResponse)


    def test_registration_filter(self):
        # Test Registration
        param = {'registration': self.cguid4}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))        
        registrationPostResponse = self.client.get(path)

        self.assertEqual(registrationPostResponse.status_code, 200)
        self.assertContains(registrationPostResponse,self.guid4)
        self.assertNotIn(self.guid2, registrationPostResponse)
        self.assertNotIn(self.guid3, registrationPostResponse)
        self.assertNotIn(self.guid1, registrationPostResponse)
        self.assertNotIn(self.guid5, registrationPostResponse)
        self.assertNotIn(self.guid6, registrationPostResponse)
        self.assertNotIn(self.guid7, registrationPostResponse)
        self.assertNotIn(self.guid8, registrationPostResponse)

    def test_actor_filter(self):
        # Test actor
        actorGetResponse = self.client.post(reverse(views.statements), {'actor':{"objectType": "person", 'name':['tester1'],'mbox':['test1@tester.com']}}, content_type="application/x-www-form-urlencoded")
        
        self.assertEqual(actorGetResponse.status_code, 200)
        self.assertContains(actorGetResponse,self.guid1)
        self.assertContains(actorGetResponse,self.guid2)
        self.assertContains(actorGetResponse,self.guid3)                
        self.assertNotIn(self.guid4, actorGetResponse)
        self.assertNotIn(self.guid5, actorGetResponse)
        self.assertNotIn(self.guid6, actorGetResponse)
        self.assertNotIn(self.guid7, actorGetResponse)
        self.assertNotIn(self.guid8, actorGetResponse)                


    def test_instructor_filter(self):
        # Test instructor - will only return one b/c actor in stmt supercedes instructor in context
        instructorGetResponse = self.client.post(reverse(views.statements), {"instructor":{"name":["bill"],"mbox":["bill@bill.com"]}},  content_type="application/x-www-form-urlencoded")
        self.assertEqual(instructorGetResponse.status_code, 200)
        self.assertContains(instructorGetResponse, self.guid4)
        self.assertNotIn(self.guid2, instructorGetResponse)
        self.assertNotIn(self.guid3, instructorGetResponse)
        self.assertNotIn(self.guid1, instructorGetResponse)
        self.assertNotIn(self.guid5, instructorGetResponse)
        self.assertNotIn(self.guid4, instructorGetResponse)
        self.assertNotIn(self.guid6, instructorGetResponse)
        self.assertNotIn(self.guid7, instructorGetResponse)
        self.assertNotIn(self.guid8, instructorGetResponse)

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
        # print sparseGetResponse.content
        # pdb.set_trace()
        self.assertEqual(sparseGetResponse.status_code, 200)
        self.assertContains(sparseGetResponse, 'definition')        
        self.assertContains(sparseGetResponse, 'firstName')
        self.assertContains(sparseGetResponse, 'lastName')
        self.assertContains(sparseGetResponse, 'givenName')
        self.assertContains(sparseGetResponse, 'familyName')
        self.assertContains(sparseGetResponse, 'account')
        self.assertContains(sparseGetResponse, 'openid')



    def test_linked_filters(self):
        # Test reasonable linked query
        param = {'verb':'created', 'object':{'objectType': 'Activity', 'id':'foogie'}, 'since':self.secondTime, 'authoritative':'False', 'sparse': False}
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode(param))        
        registrationGetResponse = self.client.get(path)
        self.assertEqual(registrationGetResponse.status_code, 200)
        self.assertContains(registrationGetResponse, self.guid2)

    def test_cors_post_put(self):
        bdy = {"statementId": "postputID"}
        # bdy['content'] = json.dumps({"statementId": "postputID","verb":"created","object": {"id":"test_cors_post_put"}})
        bdy['content'] = {"verb":"created","object": {"id":"test_cors_post_put"}}
        bdy['Authorization'] = self.auth
        bdy['Content-Type'] = "application/json"
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode({"method":"PUT"}))
        response = self.client.post(path, bdy, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 204)

        act = models.activity.objects.get(activity_id="test_cors_post_put")
        actorName = models.agent_name.objects.get(name='tester1')
        actorMbox = models.agent_mbox.objects.get(mbox='test1@tester.com')

        self.assertEqual(act.activity_id, "test_cors_post_put")

    def test_tetris_snafu(self):
        stmtid = str(uuid.uuid4())
        stmt = json.dumps({"verb":"attempted",
                            "object":{"id":"scorm.com/JsTetris_TCAPI",
                                      "definition":{"type":"media",
                                                   "name":{"en-US":"Js Tetris - Tin Can Prototype"},
                                                   "description":{"en-US":"A game of tetris."}}},
                            "context":{"contextActivities":{"grouping":{"id":"scorm.com/JsTetris_TCAPI"}},
                                       "registration":"52775f36-108d-4d68-9564-673dfa440761"},
                            "actor":{"name":["tom creighton"],"mbox":["mailto:tom@example.com"]}})
        path = '%s?%s' % (reverse(views.statements), urllib.urlencode({"statementId":stmtid}))
        putstmt = self.client.put(path, stmt, content_type="application/json", Authorization=self.auth)
        self.assertEqual(putstmt.status_code, 204)

        getstmt = self.client.get(path)
        self.assertEqual(getstmt.status_code, 200)
        self.assertContains(getstmt, stmtid)