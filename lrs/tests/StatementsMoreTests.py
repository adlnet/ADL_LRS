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
import pdb

class StatementsMoreTests(TestCase):
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
            self.guid9 = str(uuid.uuid4())
            self.guid10 = str(uuid.uuid4())

            self.guid11 = str(uuid.uuid4())
            self.guid12 = str(uuid.uuid4())
            self.guid13 = str(uuid.uuid4())    
            self.guid14 = str(uuid.uuid4())
            self.guid15 = str(uuid.uuid4())

            # Context guid
            self.cguid1 = str(uuid.uuid4())
            self.cguid2 = str(uuid.uuid4())    
            self.cguid3 = str(uuid.uuid4())
            self.cguid4 = str(uuid.uuid4())
            self.cguid5 = str(uuid.uuid4())

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
                'ckey22': 'cval22'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})        

            self.existStmt3 = json.dumps({"statement_id":self.guid3,"verb":"created", "object": {'objectType': 'Activity', 'id':'foogals',
                'definition': {'name': 'testname3','description': 'testdesc3', 'type': 'cmi.interaction',
                'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
                'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
                "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
                'duration': self.mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
                'context':{'registration': self.cguid3, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
                'revision': 'food', 'platform':'bard','language': 'en-US','instructor':{'name':['bill'], 'mbox':['bill@bill.com']} , 'extensions':{'ckey111': 'cval111',
                'ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})        

            self.existStmt4 = json.dumps({"statement_id":self.guid4,
                "verb":"passed", "object": {'objectType': 'Activity', 'id':'foogal',
                'definition': {'name': 'testname3','description': 'testdesc3', 'type': 'cmi.interaction',
                'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
                'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
                "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
                'duration': self.mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
                'context':{'registration': self.cguid4, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
                'revision': 'food', 'platform':'bard','language': 'en-US','instructor':{'name':['bill'], 'mbox':['bill@bill.com']}, 'extensions':{'ckey111': 'cval111',
                'ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})

            self.existStmt5 = json.dumps({"statement_id":self.guid5, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
                "verb":"passed"})

            self.existStmt6 = json.dumps({"statement_id":self.guid6, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
                "verb":"passed"})

            self.existStmt7 = json.dumps({"statement_id":self.guid7, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
                "verb":"passed"})

            self.existStmt8 = json.dumps({"statement_id":self.guid8, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
                "verb":"passed"})

            self.existStmt9 = json.dumps({"statement_id":self.guid9, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
                "verb":"passed"})

            self.existStmt10 = json.dumps({"statement_id":self.guid10, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
                "verb":"passed"})       

            self.existStmt11 = json.dumps({"statement_id":self.guid11, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
                "verb":"passed"})

            self.existStmt12 = json.dumps({"statement_id":self.guid12, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
                "verb":"passed"})

            self.existStmt13 = json.dumps({"statement_id":self.guid13, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
                "verb":"passed"})

            self.existStmt14 = json.dumps({"statement_id":self.guid14, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
                "verb":"passed"})

            self.existStmt15 = json.dumps({"statement_id":self.guid15, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
                "verb":"passed"})


            # Post statements
            self.postresponse1 = self.client.post(reverse(views.statements), self.existStmt1,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse2 = self.client.post(reverse(views.statements), self.existStmt2,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse3 = self.client.post(reverse(views.statements), self.existStmt3,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse4 = self.client.post(reverse(views.statements), self.existStmt4,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse5 = self.client.post(reverse(views.statements), self.existStmt5,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            
            self.postresponse6 = self.client.post(reverse(views.statements), self.existStmt6,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse7 = self.client.post(reverse(views.statements), self.existStmt7,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse8 = self.client.post(reverse(views.statements), self.existStmt8,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse9 = self.client.post(reverse(views.statements), self.existStmt9,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse10 = self.client.post(reverse(views.statements), self.existStmt10,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)

            self.postresponse11 = self.client.post(reverse(views.statements), self.existStmt11,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse12 = self.client.post(reverse(views.statements), self.existStmt12,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse13 = self.client.post(reverse(views.statements), self.existStmt13,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse14 = self.client.post(reverse(views.statements), self.existStmt14,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            self.postresponse15 = self.client.post(reverse(views.statements), self.existStmt15,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
            
            time.sleep(1)
            self.secondTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())

    def test_more_stmts_url(self):
        # Make initial complex get so 'more' will be required
        sinceGetResponse = self.client.get(reverse(views.statements), {"authoritative":{"name":["auth1"],"mbox":["auth1@example.com"]}})
        resp_json = json.loads(sinceGetResponse.content)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]
  
        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))
        
        self.assertEqual(moreURLGet.status_code, 200)
        self.assertContains(moreURLGet, self.postresponse2.content)
        self.assertContains(moreURLGet, self.postresponse3.content)                
        self.assertContains(moreURLGet, self.postresponse4.content)
        self.assertNotIn(self.postresponse1.content, moreURLGet)
        self.assertNotIn(self.postresponse5.content, moreURLGet)
        self.assertNotIn(self.postresponse6.content, moreURLGet)
        self.assertNotIn(self.postresponse7.content, moreURLGet)
        self.assertNotIn(self.postresponse8.content, moreURLGet)
        self.assertNotIn(self.postresponse9.content, moreURLGet)
        self.assertNotIn(self.postresponse10.content, moreURLGet)
        self.assertNotIn(self.postresponse11.content, moreURLGet)
        self.assertNotIn(self.postresponse12.content, moreURLGet)
        self.assertNotIn(self.postresponse13.content, moreURLGet)
        self.assertNotIn(self.postresponse14.content, moreURLGet)
        self.assertNotIn(self.postresponse15.content, moreURLGet)






