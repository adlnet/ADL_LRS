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

        self.guid16 = str(uuid.uuid4())
        self.guid17 = str(uuid.uuid4())
        self.guid18 = str(uuid.uuid4())    
        self.guid19 = str(uuid.uuid4())
        self.guid20 = str(uuid.uuid4())

        self.guid21 = str(uuid.uuid4())
        self.guid22 = str(uuid.uuid4())
        self.guid23 = str(uuid.uuid4())    
        self.guid24 = str(uuid.uuid4())
        self.guid25 = str(uuid.uuid4())


        # Context guid
        self.cguid1 = str(uuid.uuid4())
        self.cguid2 = str(uuid.uuid4())    
        self.cguid3 = str(uuid.uuid4())
        self.cguid4 = str(uuid.uuid4())
        self.cguid5 = str(uuid.uuid4())

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

        self.existStmt16 = json.dumps({"statement_id":self.guid16, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})

        self.existStmt17 = json.dumps({"statement_id":self.guid17, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})

        self.existStmt18 = json.dumps({"statement_id":self.guid18, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})

        self.existStmt19 = json.dumps({"statement_id":self.guid19, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})

        self.existStmt20 = json.dumps({"statement_id":self.guid20, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})       

        self.existStmt21 = json.dumps({"statement_id":self.guid21, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})

        self.existStmt22 = json.dumps({"statement_id":self.guid22, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})

        self.existStmt23 = json.dumps({"statement_id":self.guid23, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})

        self.existStmt24 = json.dumps({"statement_id":self.guid24, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})

        self.existStmt25 = json.dumps({"statement_id":self.guid25, "object":{'objectType':'Person','name':['jon'],'mbox':['jon@jon.com']},
            "verb":"passed"})




        # Post statements
        self.postresponse1 = self.client.post(reverse(views.statements), self.existStmt1,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse2 = self.client.post(reverse(views.statements), self.existStmt2,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse3 = self.client.post(reverse(views.statements), self.existStmt3,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse4 = self.client.post(reverse(views.statements), self.existStmt4,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse5 = self.client.post(reverse(views.statements), self.existStmt5,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)

        self.secondTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())
        time.sleep(1)
        
        self.postresponse6 = self.client.post(reverse(views.statements), self.existStmt6,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse7 = self.client.post(reverse(views.statements), self.existStmt7,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse8 = self.client.post(reverse(views.statements), self.existStmt8,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse9 = self.client.post(reverse(views.statements), self.existStmt9,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse10 = self.client.post(reverse(views.statements), self.existStmt10,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)

        self.thirdTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())
        time.sleep(1)

        self.postresponse11 = self.client.post(reverse(views.statements), self.existStmt11,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse12 = self.client.post(reverse(views.statements), self.existStmt12,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse13 = self.client.post(reverse(views.statements), self.existStmt13,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse14 = self.client.post(reverse(views.statements), self.existStmt14,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)     
        time.sleep(1)
        self.postresponse15 = self.client.post(reverse(views.statements), self.existStmt15,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)

        self.fourthTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())
        time.sleep(1)

        self.postresponse16 = self.client.post(reverse(views.statements), self.existStmt16,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse17 = self.client.post(reverse(views.statements), self.existStmt17,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse18 = self.client.post(reverse(views.statements), self.existStmt18,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse19 = self.client.post(reverse(views.statements), self.existStmt19,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse20 = self.client.post(reverse(views.statements), self.existStmt20,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)

        self.fifthTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())
        time.sleep(1)

        self.postresponse21 = self.client.post(reverse(views.statements), self.existStmt21,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse22 = self.client.post(reverse(views.statements), self.existStmt22,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse23 = self.client.post(reverse(views.statements), self.existStmt23,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time.sleep(1)
        self.postresponse24 = self.client.post(reverse(views.statements), self.existStmt24,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)

        time.sleep(1)
        self.sixthTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())

        time.sleep(1)
        self.postresponse25 = self.client.post(reverse(views.statements), self.existStmt25,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)

    def test_unknown_more_id_url(self):
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}))
        self.assertContains(moreURLGet, 'List does not exist - may have expired after 24 hours')

    def test_not_full_page_stmts(self):
        sincePostResponse = self.client.post(reverse(views.statements), {"until":self.secondTime},content_type="application/x-www-form-urlencoded")

        self.assertEqual(sincePostResponse.status_code, 200)
        self.assertContains(sincePostResponse, self.postresponse5.content)
        self.assertContains(sincePostResponse, self.postresponse4.content)                
        self.assertContains(sincePostResponse, self.postresponse3.content)
        self.assertContains(sincePostResponse, self.postresponse2.content)
        self.assertContains(sincePostResponse, self.postresponse1.content)                

        self.assertNotIn(self.postresponse25.content, sincePostResponse)
        self.assertNotIn(self.postresponse24.content, sincePostResponse)
        self.assertNotIn(self.postresponse23.content, sincePostResponse)
        self.assertNotIn(self.postresponse22.content, sincePostResponse)
        self.assertNotIn(self.postresponse21.content, sincePostResponse)
        self.assertNotIn(self.postresponse20.content, sincePostResponse)
        self.assertNotIn(self.postresponse19.content, sincePostResponse)
        self.assertNotIn(self.postresponse18.content, sincePostResponse)
        self.assertNotIn(self.postresponse17.content, sincePostResponse)
        self.assertNotIn(self.postresponse16.content, sincePostResponse)
        self.assertNotIn(self.postresponse15.content, sincePostResponse)
        self.assertNotIn(self.postresponse14.content, sincePostResponse)
        self.assertNotIn(self.postresponse13.content, sincePostResponse)
        self.assertNotIn(self.postresponse12.content, sincePostResponse)
        self.assertNotIn(self.postresponse11.content, sincePostResponse)
        self.assertNotIn(self.postresponse10.content, sincePostResponse)
        self.assertNotIn(self.postresponse9.content, sincePostResponse)
        self.assertNotIn(self.postresponse7.content, sincePostResponse)
        self.assertNotIn(self.postresponse8.content, sincePostResponse)
        self.assertNotIn(self.postresponse6.content, sincePostResponse)        

    def test_single_full_page_stmts(self):
        sincePostResponse = self.client.post(reverse(views.statements), {"until":self.thirdTime},content_type="application/x-www-form-urlencoded")

        self.assertEqual(sincePostResponse.status_code, 200)
        self.assertContains(sincePostResponse, self.postresponse10.content)
        self.assertContains(sincePostResponse, self.postresponse9.content)                
        self.assertContains(sincePostResponse, self.postresponse8.content)
        self.assertContains(sincePostResponse, self.postresponse7.content)
        self.assertContains(sincePostResponse, self.postresponse6.content)
        self.assertContains(sincePostResponse, self.postresponse5.content)
        self.assertContains(sincePostResponse, self.postresponse4.content)                
        self.assertContains(sincePostResponse, self.postresponse3.content)
        self.assertContains(sincePostResponse, self.postresponse2.content)
        self.assertContains(sincePostResponse, self.postresponse1.content)

        self.assertNotIn(self.postresponse25.content, sincePostResponse)
        self.assertNotIn(self.postresponse24.content, sincePostResponse)
        self.assertNotIn(self.postresponse23.content, sincePostResponse)
        self.assertNotIn(self.postresponse22.content, sincePostResponse)
        self.assertNotIn(self.postresponse21.content, sincePostResponse)        
        self.assertNotIn(self.postresponse20.content, sincePostResponse)
        self.assertNotIn(self.postresponse19.content, sincePostResponse)
        self.assertNotIn(self.postresponse18.content, sincePostResponse)
        self.assertNotIn(self.postresponse17.content, sincePostResponse)
        self.assertNotIn(self.postresponse16.content, sincePostResponse)
        self.assertNotIn(self.postresponse15.content, sincePostResponse)
        self.assertNotIn(self.postresponse14.content, sincePostResponse)
        self.assertNotIn(self.postresponse13.content, sincePostResponse)
        self.assertNotIn(self.postresponse12.content, sincePostResponse)
        self.assertNotIn(self.postresponse11.content, sincePostResponse)

    def test_single_full_second_not_full_more_stmts_url(self):
        sincePostResponse = self.client.post(reverse(views.statements), {"until":self.fourthTime},content_type="application/x-www-form-urlencoded")
        resp_json = json.loads(sincePostResponse.content)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertEqual(sincePostResponse.status_code, 200)
        self.assertContains(sincePostResponse, self.postresponse15.content)
        self.assertContains(sincePostResponse, self.postresponse14.content)                
        self.assertContains(sincePostResponse, self.postresponse13.content)
        self.assertContains(sincePostResponse, self.postresponse12.content)
        self.assertContains(sincePostResponse, self.postresponse11.content)
        self.assertContains(sincePostResponse, self.postresponse10.content)
        self.assertContains(sincePostResponse, self.postresponse9.content)                
        self.assertContains(sincePostResponse, self.postresponse8.content)
        self.assertContains(sincePostResponse, self.postresponse7.content)
        self.assertContains(sincePostResponse, self.postresponse6.content)

        self.assertNotIn(self.postresponse25.content, sincePostResponse)
        self.assertNotIn(self.postresponse24.content, sincePostResponse)
        self.assertNotIn(self.postresponse23.content, sincePostResponse)
        self.assertNotIn(self.postresponse22.content, sincePostResponse)
        self.assertNotIn(self.postresponse21.content, sincePostResponse)        
        self.assertNotIn(self.postresponse20.content, sincePostResponse)
        self.assertNotIn(self.postresponse19.content, sincePostResponse)
        self.assertNotIn(self.postresponse18.content, sincePostResponse)
        self.assertNotIn(self.postresponse17.content, sincePostResponse)
        self.assertNotIn(self.postresponse16.content, sincePostResponse)
        self.assertNotIn(self.postresponse5.content, sincePostResponse)
        self.assertNotIn(self.postresponse4.content, sincePostResponse)
        self.assertNotIn(self.postresponse3.content, sincePostResponse)
        self.assertNotIn(self.postresponse2.content, sincePostResponse)
        self.assertNotIn(self.postresponse1.content, sincePostResponse)

        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))

        self.assertEqual(moreURLGet.status_code, 200)
        self.assertContains(moreURLGet, self.postresponse5.content)
        self.assertContains(moreURLGet, self.postresponse4.content)
        self.assertContains(moreURLGet, self.postresponse3.content)                
        self.assertContains(moreURLGet, self.postresponse2.content)
        self.assertContains(moreURLGet, self.postresponse1.content)

        self.assertNotIn(self.postresponse24.content, moreURLGet)
        self.assertNotIn(self.postresponse23.content, moreURLGet)
        self.assertNotIn(self.postresponse22.content, moreURLGet)
        self.assertNotIn(self.postresponse21.content, moreURLGet)
        self.assertNotIn(self.postresponse20.content, moreURLGet)
        self.assertNotIn(self.postresponse19.content, moreURLGet)
        self.assertNotIn(self.postresponse18.content, moreURLGet)
        self.assertNotIn(self.postresponse17.content, moreURLGet)
        self.assertNotIn(self.postresponse16.content, moreURLGet)
        self.assertNotIn(self.postresponse15.content, moreURLGet)
        self.assertNotIn(self.postresponse14.content, moreURLGet)
        self.assertNotIn(self.postresponse13.content, moreURLGet)
        self.assertNotIn(self.postresponse12.content, moreURLGet)
        self.assertNotIn(self.postresponse11.content, moreURLGet)
        self.assertNotIn(self.postresponse10.content, moreURLGet)
        self.assertNotIn(self.postresponse9.content, moreURLGet)
        self.assertNotIn(self.postresponse8.content, moreURLGet)
        self.assertNotIn(self.postresponse7.content, moreURLGet)
        self.assertNotIn(self.postresponse6.content, moreURLGet)        
        self.assertNotIn(self.postresponse25.content, moreURLGet)

    def test_two_pages_full_more_stmts_url(self):
        sincePostResponse = self.client.post(reverse(views.statements), {"until":self.fifthTime},content_type="application/x-www-form-urlencoded")
        resp_json = json.loads(sincePostResponse.content)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertEqual(sincePostResponse.status_code, 200)
        self.assertContains(sincePostResponse, self.postresponse20.content)
        self.assertContains(sincePostResponse, self.postresponse19.content)                
        self.assertContains(sincePostResponse, self.postresponse18.content)
        self.assertContains(sincePostResponse, self.postresponse17.content)
        self.assertContains(sincePostResponse, self.postresponse16.content)
        self.assertContains(sincePostResponse, self.postresponse15.content)
        self.assertContains(sincePostResponse, self.postresponse14.content)                
        self.assertContains(sincePostResponse, self.postresponse13.content)
        self.assertContains(sincePostResponse, self.postresponse12.content)
        self.assertContains(sincePostResponse, self.postresponse11.content)

        self.assertNotIn(self.postresponse25.content, sincePostResponse)
        self.assertNotIn(self.postresponse24.content, sincePostResponse)
        self.assertNotIn(self.postresponse23.content, sincePostResponse)
        self.assertNotIn(self.postresponse22.content, sincePostResponse)
        self.assertNotIn(self.postresponse21.content, sincePostResponse)        
        self.assertNotIn(self.postresponse10.content, sincePostResponse)
        self.assertNotIn(self.postresponse9.content, sincePostResponse)
        self.assertNotIn(self.postresponse8.content, sincePostResponse)
        self.assertNotIn(self.postresponse7.content, sincePostResponse)
        self.assertNotIn(self.postresponse6.content, sincePostResponse)
        self.assertNotIn(self.postresponse5.content, sincePostResponse)
        self.assertNotIn(self.postresponse4.content, sincePostResponse)
        self.assertNotIn(self.postresponse3.content, sincePostResponse)
        self.assertNotIn(self.postresponse2.content, sincePostResponse)
        self.assertNotIn(self.postresponse1.content, sincePostResponse)

        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))

        self.assertEqual(moreURLGet.status_code, 200)
        self.assertContains(moreURLGet, self.postresponse10.content)
        self.assertContains(moreURLGet, self.postresponse9.content)
        self.assertContains(moreURLGet, self.postresponse8.content)                
        self.assertContains(moreURLGet, self.postresponse7.content)
        self.assertContains(moreURLGet, self.postresponse6.content)        
        self.assertContains(moreURLGet, self.postresponse5.content)
        self.assertContains(moreURLGet, self.postresponse4.content)
        self.assertContains(moreURLGet, self.postresponse3.content)                
        self.assertContains(moreURLGet, self.postresponse2.content)
        self.assertContains(moreURLGet, self.postresponse1.content)

        self.assertNotIn(self.postresponse24.content, moreURLGet)
        self.assertNotIn(self.postresponse23.content, moreURLGet)
        self.assertNotIn(self.postresponse22.content, moreURLGet)
        self.assertNotIn(self.postresponse21.content, moreURLGet)
        self.assertNotIn(self.postresponse20.content, moreURLGet)
        self.assertNotIn(self.postresponse19.content, moreURLGet)
        self.assertNotIn(self.postresponse18.content, moreURLGet)
        self.assertNotIn(self.postresponse17.content, moreURLGet)
        self.assertNotIn(self.postresponse16.content, moreURLGet)
        self.assertNotIn(self.postresponse15.content, moreURLGet)
        self.assertNotIn(self.postresponse14.content, moreURLGet)
        self.assertNotIn(self.postresponse13.content, moreURLGet)
        self.assertNotIn(self.postresponse12.content, moreURLGet)
        self.assertNotIn(self.postresponse11.content, moreURLGet)       
        self.assertNotIn(self.postresponse25.content, moreURLGet)

    def test_two_pages_full_third_not_full_more_stmts_url(self):
        # Make initial complex get so 'more' will be required
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime})
        resp_json = json.loads(sinceGetResponse.content)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        # print sinceGetResponse

        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertContains(sinceGetResponse, self.postresponse24.content)
        self.assertContains(sinceGetResponse, self.postresponse23.content)                
        self.assertContains(sinceGetResponse, self.postresponse22.content)
        self.assertContains(sinceGetResponse, self.postresponse21.content)
        self.assertContains(sinceGetResponse, self.postresponse20.content)                
        self.assertContains(sinceGetResponse, self.postresponse19.content)        
        self.assertContains(sinceGetResponse, self.postresponse18.content)
        self.assertContains(sinceGetResponse, self.postresponse17.content)                
        self.assertContains(sinceGetResponse, self.postresponse16.content)
        self.assertContains(sinceGetResponse, self.postresponse15.content)

        self.assertNotIn(self.postresponse14.content, sinceGetResponse)
        self.assertNotIn(self.postresponse13.content, sinceGetResponse)
        self.assertNotIn(self.postresponse12.content, sinceGetResponse)
        self.assertNotIn(self.postresponse11.content, sinceGetResponse)
        self.assertNotIn(self.postresponse10.content, sinceGetResponse)
        self.assertNotIn(self.postresponse9.content, sinceGetResponse)
        self.assertNotIn(self.postresponse8.content, sinceGetResponse)
        self.assertNotIn(self.postresponse7.content, sinceGetResponse)
        self.assertNotIn(self.postresponse6.content, sinceGetResponse)
        self.assertNotIn(self.postresponse5.content, sinceGetResponse)
        self.assertNotIn(self.postresponse4.content, sinceGetResponse)
        self.assertNotIn(self.postresponse3.content, sinceGetResponse)
        self.assertNotIn(self.postresponse2.content, sinceGetResponse)
        self.assertNotIn(self.postresponse1.content, sinceGetResponse)        
        self.assertNotIn(self.postresponse25.content, sinceGetResponse)



        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))
        more_json = json.loads(moreURLGet.content)
        more_resp_url = more_json['more']
        more_resp_id = more_resp_url[-32:]

        # print moreURLGet.content

        self.assertEqual(moreURLGet.status_code, 200)
        self.assertContains(moreURLGet, self.postresponse14.content)
        self.assertContains(moreURLGet, self.postresponse13.content)                
        self.assertContains(moreURLGet, self.postresponse12.content)
        self.assertContains(moreURLGet, self.postresponse11.content)
        self.assertContains(moreURLGet, self.postresponse10.content)                
        self.assertContains(moreURLGet, self.postresponse9.content)        
        self.assertContains(moreURLGet, self.postresponse8.content)
        self.assertContains(moreURLGet, self.postresponse7.content)                
        self.assertContains(moreURLGet, self.postresponse6.content)
        self.assertContains(moreURLGet, self.postresponse5.content)

        self.assertNotIn(self.postresponse24.content, moreURLGet)
        self.assertNotIn(self.postresponse23.content, moreURLGet)
        self.assertNotIn(self.postresponse22.content, moreURLGet)
        self.assertNotIn(self.postresponse21.content, moreURLGet)
        self.assertNotIn(self.postresponse20.content, moreURLGet)
        self.assertNotIn(self.postresponse19.content, moreURLGet)
        self.assertNotIn(self.postresponse18.content, moreURLGet)
        self.assertNotIn(self.postresponse17.content, moreURLGet)
        self.assertNotIn(self.postresponse16.content, moreURLGet)
        self.assertNotIn(self.postresponse15.content, moreURLGet)
        self.assertNotIn(self.postresponse4.content, moreURLGet)
        self.assertNotIn(self.postresponse3.content, moreURLGet)
        self.assertNotIn(self.postresponse2.content, moreURLGet)
        self.assertNotIn(self.postresponse1.content, moreURLGet)        
        self.assertNotIn(self.postresponse25.content, moreURLGet)


        more2URLGet = self.client.get(reverse(views.statements_more, kwargs={'more_id':more_resp_id}))
        # print more2URLGet
        self.assertEqual(moreURLGet.status_code, 200)
        self.assertContains(more2URLGet, self.postresponse4.content)
        self.assertContains(more2URLGet, self.postresponse3.content)                
        self.assertContains(more2URLGet, self.postresponse2.content)
        self.assertContains(more2URLGet, self.postresponse1.content)

        self.assertNotIn(self.postresponse25.content, more2URLGet)
        self.assertNotIn(self.postresponse24.content, more2URLGet)
        self.assertNotIn(self.postresponse23.content, more2URLGet)
        self.assertNotIn(self.postresponse22.content, more2URLGet)
        self.assertNotIn(self.postresponse21.content, more2URLGet)
        self.assertNotIn(self.postresponse20.content, more2URLGet)
        self.assertNotIn(self.postresponse19.content, more2URLGet)
        self.assertNotIn(self.postresponse18.content, more2URLGet)
        self.assertNotIn(self.postresponse17.content, more2URLGet)
        self.assertNotIn(self.postresponse16.content, more2URLGet)
        self.assertNotIn(self.postresponse15.content, more2URLGet)
        self.assertNotIn(self.postresponse14.content, more2URLGet)
        self.assertNotIn(self.postresponse13.content, more2URLGet)
        self.assertNotIn(self.postresponse12.content, more2URLGet)
        self.assertNotIn(self.postresponse11.content, more2URLGet)        
        self.assertNotIn(self.postresponse10.content, more2URLGet)
        self.assertNotIn(self.postresponse9.content, more2URLGet)
        self.assertNotIn(self.postresponse8.content, more2URLGet)
        self.assertNotIn(self.postresponse7.content, more2URLGet)
        self.assertNotIn(self.postresponse6.content, more2URLGet)
        self.assertNotIn(self.postresponse5.content, more2URLGet)        
    
    def test_limit_less_than_server_limit(self):
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime, "limit":8})
        resp_json = json.loads(sinceGetResponse.content)

        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertEqual(len(resp_json['statements']), 8)        
        self.assertContains(sinceGetResponse, self.postresponse24.content)
        self.assertContains(sinceGetResponse, self.postresponse23.content)                
        self.assertContains(sinceGetResponse, self.postresponse22.content)
        self.assertContains(sinceGetResponse, self.postresponse21.content)
        self.assertContains(sinceGetResponse, self.postresponse20.content)                
        self.assertContains(sinceGetResponse, self.postresponse19.content)        
        self.assertContains(sinceGetResponse, self.postresponse18.content)
        self.assertContains(sinceGetResponse, self.postresponse17.content)    

        self.assertNotIn(self.postresponse16.content, sinceGetResponse)
        self.assertNotIn(self.postresponse15.content, sinceGetResponse)
        self.assertNotIn(self.postresponse14.content, sinceGetResponse)
        self.assertNotIn(self.postresponse13.content, sinceGetResponse)
        self.assertNotIn(self.postresponse12.content, sinceGetResponse)
        self.assertNotIn(self.postresponse11.content, sinceGetResponse)
        self.assertNotIn(self.postresponse10.content, sinceGetResponse)
        self.assertNotIn(self.postresponse9.content, sinceGetResponse)
        self.assertNotIn(self.postresponse8.content, sinceGetResponse)
        self.assertNotIn(self.postresponse7.content, sinceGetResponse)
        self.assertNotIn(self.postresponse6.content, sinceGetResponse)
        self.assertNotIn(self.postresponse5.content, sinceGetResponse)
        self.assertNotIn(self.postresponse4.content, sinceGetResponse)
        self.assertNotIn(self.postresponse3.content, sinceGetResponse)
        self.assertNotIn(self.postresponse2.content, sinceGetResponse)
        self.assertNotIn(self.postresponse1.content, sinceGetResponse)                
        self.assertNotIn(self.postresponse25.content, sinceGetResponse)
        self.assertNotIn('more', sinceGetResponse)


    def test_limit_same_as_server_limit(self):
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime, "limit":10})
        resp_json = json.loads(sinceGetResponse.content)

        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertEqual(len(resp_json['statements']), 10)        
        self.assertContains(sinceGetResponse, self.postresponse24.content)
        self.assertContains(sinceGetResponse, self.postresponse23.content)                
        self.assertContains(sinceGetResponse, self.postresponse22.content)
        self.assertContains(sinceGetResponse, self.postresponse21.content)
        self.assertContains(sinceGetResponse, self.postresponse20.content)                
        self.assertContains(sinceGetResponse, self.postresponse19.content)        
        self.assertContains(sinceGetResponse, self.postresponse18.content)
        self.assertContains(sinceGetResponse, self.postresponse17.content)    
        self.assertContains(sinceGetResponse, self.postresponse16.content)
        self.assertContains(sinceGetResponse, self.postresponse15.content)    

        self.assertNotIn(self.postresponse14.content, sinceGetResponse)
        self.assertNotIn(self.postresponse13.content, sinceGetResponse)
        self.assertNotIn(self.postresponse12.content, sinceGetResponse)
        self.assertNotIn(self.postresponse11.content, sinceGetResponse)
        self.assertNotIn(self.postresponse10.content, sinceGetResponse)
        self.assertNotIn(self.postresponse9.content, sinceGetResponse)
        self.assertNotIn(self.postresponse8.content, sinceGetResponse)
        self.assertNotIn(self.postresponse7.content, sinceGetResponse)
        self.assertNotIn(self.postresponse6.content, sinceGetResponse)
        self.assertNotIn(self.postresponse5.content, sinceGetResponse)
        self.assertNotIn(self.postresponse4.content, sinceGetResponse)
        self.assertNotIn(self.postresponse3.content, sinceGetResponse)
        self.assertNotIn(self.postresponse2.content, sinceGetResponse)
        self.assertNotIn(self.postresponse1.content, sinceGetResponse)                
        self.assertNotIn(self.postresponse25.content, sinceGetResponse)
        self.assertNotIn('more', sinceGetResponse)    

    def test_limit_more_than_server_limit(self):
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime, "limit":12})
        resp_json = json.loads(sinceGetResponse.content)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertEqual(len(resp_json['statements']), 10)        
        self.assertContains(sinceGetResponse, self.postresponse24.content)
        self.assertContains(sinceGetResponse, self.postresponse23.content)                
        self.assertContains(sinceGetResponse, self.postresponse22.content)
        self.assertContains(sinceGetResponse, self.postresponse21.content)
        self.assertContains(sinceGetResponse, self.postresponse20.content)                
        self.assertContains(sinceGetResponse, self.postresponse19.content)        
        self.assertContains(sinceGetResponse, self.postresponse18.content)
        self.assertContains(sinceGetResponse, self.postresponse17.content)    
        self.assertContains(sinceGetResponse, self.postresponse16.content)
        self.assertContains(sinceGetResponse, self.postresponse15.content)    

        self.assertNotIn(self.postresponse14.content, sinceGetResponse)
        self.assertNotIn(self.postresponse13.content, sinceGetResponse)
        self.assertNotIn(self.postresponse12.content, sinceGetResponse)
        self.assertNotIn(self.postresponse11.content, sinceGetResponse)
        self.assertNotIn(self.postresponse10.content, sinceGetResponse)
        self.assertNotIn(self.postresponse9.content, sinceGetResponse)
        self.assertNotIn(self.postresponse8.content, sinceGetResponse)
        self.assertNotIn(self.postresponse7.content, sinceGetResponse)
        self.assertNotIn(self.postresponse6.content, sinceGetResponse)
        self.assertNotIn(self.postresponse5.content, sinceGetResponse)
        self.assertNotIn(self.postresponse4.content, sinceGetResponse)
        self.assertNotIn(self.postresponse3.content, sinceGetResponse)
        self.assertNotIn(self.postresponse2.content, sinceGetResponse)
        self.assertNotIn(self.postresponse1.content, sinceGetResponse)                
        self.assertNotIn(self.postresponse25.content, sinceGetResponse)

        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))
        self.assertEqual(moreURLGet.status_code, 200)
        self.assertContains(moreURLGet, self.postresponse14.content)
        self.assertContains(moreURLGet, self.postresponse13.content)

        self.assertNotIn(self.postresponse24.content, moreURLGet)
        self.assertNotIn(self.postresponse23.content, moreURLGet)
        self.assertNotIn(self.postresponse22.content, moreURLGet)
        self.assertNotIn(self.postresponse21.content, moreURLGet)
        self.assertNotIn(self.postresponse20.content, moreURLGet)
        self.assertNotIn(self.postresponse19.content, moreURLGet)
        self.assertNotIn(self.postresponse18.content, moreURLGet)
        self.assertNotIn(self.postresponse17.content, moreURLGet)
        self.assertNotIn(self.postresponse16.content, moreURLGet)
        self.assertNotIn(self.postresponse15.content, moreURLGet)
        self.assertNotIn(self.postresponse12.content, moreURLGet)
        self.assertNotIn(self.postresponse11.content, moreURLGet)
        self.assertNotIn(self.postresponse10.content, moreURLGet)
        self.assertNotIn(self.postresponse9.content, moreURLGet)
        self.assertNotIn(self.postresponse8.content, moreURLGet)
        self.assertNotIn(self.postresponse7.content, moreURLGet)
        self.assertNotIn(self.postresponse6.content, moreURLGet)
        self.assertNotIn(self.postresponse5.content, moreURLGet)
        self.assertNotIn(self.postresponse4.content, moreURLGet)
        self.assertNotIn(self.postresponse3.content, moreURLGet)
        self.assertNotIn(self.postresponse2.content, moreURLGet)
        self.assertNotIn(self.postresponse1.content, moreURLGet)        
        self.assertNotIn(self.postresponse25.content, moreURLGet)


    # To run test, change CACHE TIMEOUT to 30 in settings.py
    # def test_more_stmts_expired(self):
    #     # Make initial complex get so 'more' will be required
    #     sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.secondTime})
    #     resp_json = json.loads(sinceGetResponse.content)
    #     resp_url = resp_json['more']
    #     resp_id = resp_url[-32:]

    #     time.sleep(35)

    #     # Simulate user clicking returned 'more' URL
    #     moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))
    #     self.assertContains(moreURLGet, 'List does not exist - may have expired after 24 hours')


