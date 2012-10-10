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
import pdb
from lrs.util import retrieve_statement

class StatementsMoreTests(TestCase):
    def setUp(self):
        self.username = "tester2"
        self.email = "test2@tester.com"
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
            'definition': {'name': {'en-US':'testname2', 'en-GB':'altname'},'description': {'en-US':'testdesc2',
            'en-GB':'altdesc'}, 'type': 'cmi.interaction','interactionType': 'fill-in',
            'correctResponsesPattern': ['answer'],'extensions': {'key1': 'value1', 'key2': 'value2','key3': 'value3'}}}, 
            "result": {'score':{'scaled':.85}, 'completion': True, 'success': True, 'response': 'kicked',
            'duration': self.mytime, 'extensions':{'key1': 'value1', 'key2':'value2'}},
            'context':{'registration': self.cguid1, 'contextActivities': {'other': {'id': 'NewActivityID2'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey1': 'cval1',
            'ckey2': 'cval2'}}, 'authority':{'objectType':'Agent','name':['auth'],'mbox':['auth@example.com']}})        

        self.existStmt2 = json.dumps({"statement_id":self.guid2,"verb":"created", "object": {'objectType': 'Activity', 'id':'foogie',
            'definition': {'name': {'en-US':'testname3'},'description': {'en-US':'testdesc3'}, 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key11': 'value11', 'key22': 'value22','key33': 'value33'}}}, 
            "result": {'score':{'scaled':.75}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid2, 'contextActivities': {'other': {'id': 'NewActivityID24'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey11': 'cval11',
            'ckey22': 'cval22'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})        

        self.existStmt3 = json.dumps({"statement_id":self.guid3,"verb":"created", "object": {'objectType': 'Activity', 'id':'foogals',
            'definition': {'name': {'en-US':'testname3'},'description': {'en-US':'testdesc3'}, 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
            "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid3, 'contextActivities': {'other': {'id': 'NewActivityID23'}},
            'revision': 'food', 'platform':'bard','language': 'en-US','instructor':{'name':['bill'], 'mbox':['bill@bill.com']} , 'extensions':{'ckey111': 'cval111',
            'ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})        

        self.existStmt4 = json.dumps({"statement_id":self.guid4,
            "verb":"passed", "object": {'objectType': 'Activity', 'id':'foogal',
            'definition': {'name': {'en-US':'testname3'},'description': {'en-US':'testdesc3'}, 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
            "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid4, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
            'revision': 'food', 'platform':'bard','language': 'en-US','instructor':{'name':['bill'], 'mbox':['bill@bill.com']}, 'extensions':{'ckey111': 'cval111',
            'ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':['auth1'],'mbox':['auth1@example.com']}})

        self.existStmt5 = json.dumps({"statement_id":self.guid5, "object":{'objectType':'Person','name':['jon1'],'mbox':['jon1@jon.com']},
            "verb":"passed"})

        self.existStmt6 = json.dumps({"statement_id":self.guid6, "object":{'objectType':'Person','name':['jon2'],'mbox':['jon2@jon.com']},
            "verb":"passed"})

        self.existStmt7 = json.dumps({"statement_id":self.guid7, "object":{'objectType':'Person','name':['jon3'],'mbox':['jon3@jon.com']},
            "verb":"passed"})

        self.existStmt8 = json.dumps({"statement_id":self.guid8, "object":{'objectType':'Person','name':['jon4'],'mbox':['jon4@jon.com']},
            "verb":"passed"})

        self.existStmt9 = json.dumps({"statement_id":self.guid9, "object":{'objectType':'Person','name':['jon5'],'mbox':['jon5@jon.com']},
            "verb":"passed"})

        self.existStmt10 = json.dumps({"statement_id":self.guid10, "object":{'objectType':'Person','name':['jon33'],'mbox':['jon33@jon.com']},
            "verb":"passed"})       

        self.existStmt11 = json.dumps({"statement_id":self.guid11, "object":{'objectType':'Person','name':['jon6'],'mbox':['jon6@jon.com']},
            "verb":"passed"})

        self.existStmt12 = json.dumps({"statement_id":self.guid12, "object":{'objectType':'Person','name':['jon7'],'mbox':['jon7@jon.com']},
            "verb":"passed"})

        self.existStmt13 = json.dumps({"statement_id":self.guid13, "object":{'objectType':'Person','name':['jon8'],'mbox':['jon8@jon.com']},
            "verb":"passed"})

        self.existStmt14 = json.dumps({"statement_id":self.guid14, "object":{'objectType':'Person','name':['jon9'],'mbox':['jon9@jon.com']},
            "verb":"passed"})

        self.existStmt15 = json.dumps({"statement_id":self.guid15, "object":{'objectType':'Person','name':['jon10'],'mbox':['jon10@jon.com']},
            "verb":"passed"})

        self.existStmt16 = json.dumps({"statement_id":self.guid16, "object":{'objectType':'Person','name':['jon11'],'mbox':['jon11@jon.com']},
            "verb":"passed"})

        self.existStmt17 = json.dumps({"statement_id":self.guid17, "object":{'objectType':'Person','name':['jon12'],'mbox':['jon12@jon.com']},
            "verb":"passed"})

        self.existStmt18 = json.dumps({"statement_id":self.guid18, "object":{'objectType':'Person','name':['jon13'],'mbox':['jon13@jon.com']},
            "verb":"passed"})

        self.existStmt19 = json.dumps({"statement_id":self.guid19, "object":{'objectType':'Person','name':['jon14'],'mbox':['jon14@jon.com']},
            "verb":"passed"})

        self.existStmt20 = json.dumps({"statement_id":self.guid20, "object":{'objectType':'Person','name':['jon15'],'mbox':['jon15@jon.com']},
            "verb":"passed"})       

        self.existStmt21 = json.dumps({"statement_id":self.guid21, "object":{'objectType':'Person','name':['jon16'],'mbox':['jon16@jon.com']},
            "verb":"passed"})

        self.existStmt22 = json.dumps({"statement_id":self.guid22, "object":{'objectType':'Person','name':['jon17'],'mbox':['jon17@jon.com']},
            "verb":"passed"})

        self.existStmt23 = json.dumps({"statement_id":self.guid23, "object":{'objectType':'Person','name':['jon18'],'mbox':['jon18@jon.com']},
            "verb":"passed"})

        self.existStmt24 = json.dumps({"statement_id":self.guid24, "object":{'objectType':'Person','name':['jon19'],'mbox':['jon19@jon.com']},
            "verb":"passed"})

        self.existStmt25 = json.dumps({"statement_id":self.guid25, "object":{'objectType':'Person','name':['jon20'],'mbox':['jon20@jon.com']},
            "verb":"passed"})



        # Post statements
        self.postresponse1 = self.client.post(reverse(views.statements), self.existStmt1,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=1)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid1).update(stored=time)


        self.postresponse2 = self.client.post(reverse(views.statements), self.existStmt2,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=2)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid2).update(stored=time)


        self.postresponse3 = self.client.post(reverse(views.statements), self.existStmt3,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=3)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid3).update(stored=time)


        self.postresponse4 = self.client.post(reverse(views.statements), self.existStmt4,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=4)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid4).update(stored=time)


        self.postresponse5 = self.client.post(reverse(views.statements), self.existStmt5,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=5)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid5).update(stored=time)

        self.secondTime = str((datetime.utcnow()+timedelta(seconds=6)).replace(tzinfo=utc).isoformat())

        self.postresponse6 = self.client.post(reverse(views.statements), self.existStmt6,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=7)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid6).update(stored=time)


        self.postresponse7 = self.client.post(reverse(views.statements), self.existStmt7,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=8)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid7).update(stored=time)


        self.postresponse8 = self.client.post(reverse(views.statements), self.existStmt8,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=9)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid8).update(stored=time)


        self.postresponse9 = self.client.post(reverse(views.statements), self.existStmt9,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=10)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid9).update(stored=time)


        self.postresponse10 = self.client.post(reverse(views.statements), self.existStmt10,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=11)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid10).update(stored=time)


        self.thirdTime = str((datetime.utcnow()+timedelta(seconds=12)).replace(tzinfo=utc).isoformat())


        self.postresponse11 = self.client.post(reverse(views.statements), self.existStmt11,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=13)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid11).update(stored=time)


        self.postresponse12 = self.client.post(reverse(views.statements), self.existStmt12,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=14)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid12).update(stored=time)


        self.postresponse13 = self.client.post(reverse(views.statements), self.existStmt13,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=15)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid13).update(stored=time)


        self.postresponse14 = self.client.post(reverse(views.statements), self.existStmt14,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)     
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=16)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid14).update(stored=time)


        self.postresponse15 = self.client.post(reverse(views.statements), self.existStmt15,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=17)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid15).update(stored=time)


        self.fourthTime = str((datetime.utcnow()+timedelta(seconds=18)).replace(tzinfo=utc).isoformat())


        self.postresponse16 = self.client.post(reverse(views.statements), self.existStmt16,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=19)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid16).update(stored=time)


        self.postresponse17 = self.client.post(reverse(views.statements), self.existStmt17,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=20)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid17).update(stored=time)


        self.postresponse18 = self.client.post(reverse(views.statements), self.existStmt18,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=21)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid18).update(stored=time)


        self.postresponse19 = self.client.post(reverse(views.statements), self.existStmt19,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=22)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid19).update(stored=time)


        self.postresponse20 = self.client.post(reverse(views.statements), self.existStmt20,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=23)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid20).update(stored=time)

        self.fifthTime = str((datetime.utcnow()+timedelta(seconds=24)).replace(tzinfo=utc).isoformat())
 
        self.postresponse21 = self.client.post(reverse(views.statements), self.existStmt21,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=25)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid21).update(stored=time)


        self.postresponse22 = self.client.post(reverse(views.statements), self.existStmt22,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=26)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid22).update(stored=time)

        self.postresponse23 = self.client.post(reverse(views.statements), self.existStmt23,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=27)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid23).update(stored=time)

        self.postresponse24 = self.client.post(reverse(views.statements), self.existStmt24,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=28)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid24).update(stored=time)


        self.sixthTime = str((datetime.utcnow()+timedelta(seconds=29)).replace(tzinfo=utc).isoformat())

        self.postresponse25 = self.client.post(reverse(views.statements), self.existStmt25,  content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=30)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid25).update(stored=time)


    def test_unknown_more_id_url(self):
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}))
        self.assertContains(moreURLGet, 'List does not exist - may have expired after 24 hours')

    def test_not_full_page_stmts(self):
        sincePostResponse = self.client.post(reverse(views.statements), {"until":self.secondTime},content_type="application/x-www-form-urlencoded")

        self.assertEqual(sincePostResponse.status_code, 200)
        self.assertContains(sincePostResponse, self.guid5)
        self.assertContains(sincePostResponse, self.guid4)                
        self.assertContains(sincePostResponse, self.guid3)
        self.assertContains(sincePostResponse, self.guid2)
        self.assertContains(sincePostResponse, self.guid1)                

        self.assertNotIn(self.guid25, sincePostResponse)
        self.assertNotIn(self.guid24, sincePostResponse)
        self.assertNotIn(self.guid23, sincePostResponse)
        self.assertNotIn(self.guid22, sincePostResponse)
        self.assertNotIn(self.guid21, sincePostResponse)
        self.assertNotIn(self.guid20, sincePostResponse)
        self.assertNotIn(self.guid19, sincePostResponse)
        self.assertNotIn(self.guid18, sincePostResponse)
        self.assertNotIn(self.guid17, sincePostResponse)
        self.assertNotIn(self.guid16, sincePostResponse)
        self.assertNotIn(self.guid15, sincePostResponse)
        self.assertNotIn(self.guid14, sincePostResponse)
        self.assertNotIn(self.guid13, sincePostResponse)
        self.assertNotIn(self.guid12, sincePostResponse)
        self.assertNotIn(self.guid11, sincePostResponse)
        self.assertNotIn(self.guid10, sincePostResponse)
        self.assertNotIn(self.guid9, sincePostResponse)
        self.assertNotIn(self.guid7, sincePostResponse)
        self.assertNotIn(self.guid8, sincePostResponse)
        self.assertNotIn(self.guid6, sincePostResponse)        

    def test_single_full_page_stmts(self):
        sincePostResponse = self.client.post(reverse(views.statements), {"until":self.thirdTime},content_type="application/x-www-form-urlencoded")

        self.assertEqual(sincePostResponse.status_code, 200)
        self.assertContains(sincePostResponse, self.guid10)
        self.assertContains(sincePostResponse, self.guid9)                
        self.assertContains(sincePostResponse, self.guid8)
        self.assertContains(sincePostResponse, self.guid7)
        self.assertContains(sincePostResponse, self.guid6)
        self.assertContains(sincePostResponse, self.guid5)
        self.assertContains(sincePostResponse, self.guid4)               
        self.assertContains(sincePostResponse, self.guid3)
        self.assertContains(sincePostResponse, self.guid2)
        self.assertContains(sincePostResponse, self.guid1)

        self.assertNotIn(self.guid25, sincePostResponse)
        self.assertNotIn(self.guid24, sincePostResponse)
        self.assertNotIn(self.guid23, sincePostResponse)
        self.assertNotIn(self.guid22, sincePostResponse)
        self.assertNotIn(self.guid21, sincePostResponse)        
        self.assertNotIn(self.guid20, sincePostResponse)
        self.assertNotIn(self.guid19, sincePostResponse)
        self.assertNotIn(self.guid18, sincePostResponse)
        self.assertNotIn(self.guid17, sincePostResponse)
        self.assertNotIn(self.guid16, sincePostResponse)
        self.assertNotIn(self.guid15, sincePostResponse)
        self.assertNotIn(self.guid14, sincePostResponse)
        self.assertNotIn(self.guid13, sincePostResponse)
        self.assertNotIn(self.guid12, sincePostResponse)
        self.assertNotIn(self.guid11, sincePostResponse)

    def test_single_full_second_not_full_more_stmts_url(self):
        sincePostResponse = self.client.post(reverse(views.statements), {"until":self.fourthTime},content_type="application/x-www-form-urlencoded")
        resp_json = json.loads(sincePostResponse.content)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertEqual(sincePostResponse.status_code, 200)
        self.assertContains(sincePostResponse, self.guid15)
        self.assertContains(sincePostResponse, self.guid14)                
        self.assertContains(sincePostResponse, self.guid13)
        self.assertContains(sincePostResponse, self.guid12)
        self.assertContains(sincePostResponse, self.guid11)
        self.assertContains(sincePostResponse, self.guid10)
        self.assertContains(sincePostResponse, self.guid9)                
        self.assertContains(sincePostResponse, self.guid8)
        self.assertContains(sincePostResponse, self.guid7)
        self.assertContains(sincePostResponse, self.guid6)

        self.assertNotIn(self.guid25, sincePostResponse)
        self.assertNotIn(self.guid24, sincePostResponse)
        self.assertNotIn(self.guid23, sincePostResponse)
        self.assertNotIn(self.guid22, sincePostResponse)
        self.assertNotIn(self.guid21, sincePostResponse)        
        self.assertNotIn(self.guid20, sincePostResponse)
        self.assertNotIn(self.guid19, sincePostResponse)
        self.assertNotIn(self.guid18, sincePostResponse)
        self.assertNotIn(self.guid17, sincePostResponse)
        self.assertNotIn(self.guid16, sincePostResponse)
        self.assertNotIn(self.guid5, sincePostResponse)
        self.assertNotIn(self.guid4, sincePostResponse)
        self.assertNotIn(self.guid3, sincePostResponse)
        self.assertNotIn(self.guid2, sincePostResponse)
        self.assertNotIn(self.guid1, sincePostResponse)

        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))

        self.assertEqual(moreURLGet.status_code, 200)
        self.assertContains(moreURLGet, self.guid5)
        self.assertContains(moreURLGet, self.guid4)
        self.assertContains(moreURLGet, self.guid3)               
        self.assertContains(moreURLGet, self.guid2)
        self.assertContains(moreURLGet, self.guid1)

        self.assertNotIn(self.guid24, moreURLGet)
        self.assertNotIn(self.guid23, moreURLGet)
        self.assertNotIn(self.guid22, moreURLGet)
        self.assertNotIn(self.guid21, moreURLGet)
        self.assertNotIn(self.guid20, moreURLGet)
        self.assertNotIn(self.guid19, moreURLGet)
        self.assertNotIn(self.guid18, moreURLGet)
        self.assertNotIn(self.guid17, moreURLGet)
        self.assertNotIn(self.guid16, moreURLGet)
        self.assertNotIn(self.guid15, moreURLGet)
        self.assertNotIn(self.guid14, moreURLGet)
        self.assertNotIn(self.guid13, moreURLGet)
        self.assertNotIn(self.guid12, moreURLGet)
        self.assertNotIn(self.guid11, moreURLGet)
        self.assertNotIn(self.guid10, moreURLGet)
        self.assertNotIn(self.guid9, moreURLGet)
        self.assertNotIn(self.guid8, moreURLGet)
        self.assertNotIn(self.guid7, moreURLGet)
        self.assertNotIn(self.guid6, moreURLGet)        
        self.assertNotIn(self.guid25, moreURLGet)

    def test_two_pages_full_more_stmts_url(self):
        sincePostResponse = self.client.post(reverse(views.statements), {"until":self.fifthTime},content_type="application/x-www-form-urlencoded")
        resp_json = json.loads(sincePostResponse.content)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertEqual(sincePostResponse.status_code, 200)
        self.assertContains(sincePostResponse, self.guid20)
        self.assertContains(sincePostResponse, self.guid19)                
        self.assertContains(sincePostResponse, self.guid18)
        self.assertContains(sincePostResponse, self.guid17)
        self.assertContains(sincePostResponse, self.guid16)
        self.assertContains(sincePostResponse, self.guid15)
        self.assertContains(sincePostResponse, self.guid14)                
        self.assertContains(sincePostResponse, self.guid13)
        self.assertContains(sincePostResponse, self.guid12)
        self.assertContains(sincePostResponse, self.guid11)

        self.assertNotIn(self.guid25, sincePostResponse)
        self.assertNotIn(self.guid24, sincePostResponse)
        self.assertNotIn(self.guid23, sincePostResponse)
        self.assertNotIn(self.guid22, sincePostResponse)
        self.assertNotIn(self.guid21, sincePostResponse)        
        self.assertNotIn(self.guid10, sincePostResponse)
        self.assertNotIn(self.guid9, sincePostResponse)
        self.assertNotIn(self.guid8, sincePostResponse)
        self.assertNotIn(self.guid7, sincePostResponse)
        self.assertNotIn(self.guid6, sincePostResponse)
        self.assertNotIn(self.guid5, sincePostResponse)
        self.assertNotIn(self.guid4, sincePostResponse)
        self.assertNotIn(self.guid3, sincePostResponse)
        self.assertNotIn(self.guid2, sincePostResponse)
        self.assertNotIn(self.guid1, sincePostResponse)

        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))

        self.assertEqual(moreURLGet.status_code, 200)
        self.assertContains(moreURLGet, self.guid10)
        self.assertContains(moreURLGet, self.guid9)
        self.assertContains(moreURLGet, self.guid8)                
        self.assertContains(moreURLGet, self.guid7)
        self.assertContains(moreURLGet, self.guid6)        
        self.assertContains(moreURLGet, self.guid5)
        self.assertContains(moreURLGet, self.guid4)
        self.assertContains(moreURLGet, self.guid3)                
        self.assertContains(moreURLGet, self.guid2)
        self.assertContains(moreURLGet, self.guid1)

        self.assertNotIn(self.guid24, moreURLGet)
        self.assertNotIn(self.guid23, moreURLGet)
        self.assertNotIn(self.guid22, moreURLGet)
        self.assertNotIn(self.guid21, moreURLGet)
        self.assertNotIn(self.guid20, moreURLGet)
        self.assertNotIn(self.guid19, moreURLGet)
        self.assertNotIn(self.guid18, moreURLGet)
        self.assertNotIn(self.guid17, moreURLGet)
        self.assertNotIn(self.guid16, moreURLGet)
        self.assertNotIn(self.guid15, moreURLGet)
        self.assertNotIn(self.guid14, moreURLGet)
        self.assertNotIn(self.guid13, moreURLGet)
        self.assertNotIn(self.guid12, moreURLGet)
        self.assertNotIn(self.guid11, moreURLGet)       
        self.assertNotIn(self.guid25, moreURLGet)

    def test_two_pages_full_third_not_full_more_stmts_url(self):
        # Make initial complex get so 'more' will be required
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime})
        resp_json = json.loads(sinceGetResponse.content)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertContains(sinceGetResponse, self.guid24)
        self.assertContains(sinceGetResponse, self.guid23)                
        self.assertContains(sinceGetResponse, self.guid22)
        self.assertContains(sinceGetResponse, self.guid21)
        self.assertContains(sinceGetResponse, self.guid20)                
        self.assertContains(sinceGetResponse, self.guid19)        
        self.assertContains(sinceGetResponse, self.guid18)
        self.assertContains(sinceGetResponse, self.guid17)                
        self.assertContains(sinceGetResponse, self.guid16)
        self.assertContains(sinceGetResponse, self.guid15)

        self.assertNotIn(self.guid14, sinceGetResponse)
        self.assertNotIn(self.guid13, sinceGetResponse)
        self.assertNotIn(self.guid12, sinceGetResponse)
        self.assertNotIn(self.guid11, sinceGetResponse)
        self.assertNotIn(self.guid10, sinceGetResponse)
        self.assertNotIn(self.guid9, sinceGetResponse)
        self.assertNotIn(self.guid8, sinceGetResponse)
        self.assertNotIn(self.guid7, sinceGetResponse)
        self.assertNotIn(self.guid6, sinceGetResponse)
        self.assertNotIn(self.guid5, sinceGetResponse)
        self.assertNotIn(self.guid4, sinceGetResponse)
        self.assertNotIn(self.guid3, sinceGetResponse)
        self.assertNotIn(self.guid2, sinceGetResponse)
        self.assertNotIn(self.guid1, sinceGetResponse)        
        self.assertNotIn(self.guid25, sinceGetResponse)

        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))
        more_json = json.loads(moreURLGet.content)
        more_resp_url = more_json['more']
        more_resp_id = more_resp_url[-32:]

        self.assertEqual(moreURLGet.status_code, 200)
        self.assertContains(moreURLGet, self.guid14)
        self.assertContains(moreURLGet, self.guid13)                
        self.assertContains(moreURLGet, self.guid12)
        self.assertContains(moreURLGet, self.guid11)
        self.assertContains(moreURLGet, self.guid10)                
        self.assertContains(moreURLGet, self.guid9)        
        self.assertContains(moreURLGet, self.guid8)
        self.assertContains(moreURLGet, self.guid7)                
        self.assertContains(moreURLGet, self.guid6)
        self.assertContains(moreURLGet, self.guid5)

        self.assertNotIn(self.guid24, moreURLGet)
        self.assertNotIn(self.guid23, moreURLGet)
        self.assertNotIn(self.guid22, moreURLGet)
        self.assertNotIn(self.guid21, moreURLGet)
        self.assertNotIn(self.guid20, moreURLGet)
        self.assertNotIn(self.guid19, moreURLGet)
        self.assertNotIn(self.guid18, moreURLGet)
        self.assertNotIn(self.guid17, moreURLGet)
        self.assertNotIn(self.guid16, moreURLGet)
        self.assertNotIn(self.guid15, moreURLGet)
        self.assertNotIn(self.guid4, moreURLGet)
        self.assertNotIn(self.guid3, moreURLGet)
        self.assertNotIn(self.guid2, moreURLGet)
        self.assertNotIn(self.guid1, moreURLGet)        
        self.assertNotIn(self.guid25, moreURLGet)


        more2URLGet = self.client.get(reverse(views.statements_more, kwargs={'more_id':more_resp_id}))
        self.assertEqual(more2URLGet.status_code, 200)
        self.assertContains(more2URLGet, self.guid4)
        self.assertContains(more2URLGet, self.guid3)                
        self.assertContains(more2URLGet, self.guid2)
        self.assertContains(more2URLGet, self.guid1)

        self.assertNotIn(self.guid25, more2URLGet)
        self.assertNotIn(self.guid24, more2URLGet)
        self.assertNotIn(self.guid23, more2URLGet)
        self.assertNotIn(self.guid22, more2URLGet)
        self.assertNotIn(self.guid21, more2URLGet)
        self.assertNotIn(self.guid20, more2URLGet)
        self.assertNotIn(self.guid19, more2URLGet)
        self.assertNotIn(self.guid18, more2URLGet)
        self.assertNotIn(self.guid17, more2URLGet)
        self.assertNotIn(self.guid16, more2URLGet)
        self.assertNotIn(self.guid15, more2URLGet)
        self.assertNotIn(self.guid14, more2URLGet)
        self.assertNotIn(self.guid13, more2URLGet)
        self.assertNotIn(self.guid12, more2URLGet)
        self.assertNotIn(self.guid11, more2URLGet)        
        self.assertNotIn(self.guid10, more2URLGet)
        self.assertNotIn(self.guid9, more2URLGet)
        self.assertNotIn(self.guid8, more2URLGet)
        self.assertNotIn(self.guid7, more2URLGet)
        self.assertNotIn(self.guid6, more2URLGet)
        self.assertNotIn(self.guid5, more2URLGet)        
    
    def test_limit_less_than_server_limit(self):
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime, "limit":8})
        resp_json = json.loads(sinceGetResponse.content)

        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertEqual(len(resp_json['statements']), 8)        
        self.assertContains(sinceGetResponse, self.guid24)
        self.assertContains(sinceGetResponse, self.guid23)                
        self.assertContains(sinceGetResponse, self.guid22)
        self.assertContains(sinceGetResponse, self.guid21)
        self.assertContains(sinceGetResponse, self.guid20)                
        self.assertContains(sinceGetResponse, self.guid19)        
        self.assertContains(sinceGetResponse, self.guid18)
        self.assertContains(sinceGetResponse, self.guid17)    

        self.assertNotIn(self.guid16, sinceGetResponse)
        self.assertNotIn(self.guid15, sinceGetResponse)
        self.assertNotIn(self.guid14, sinceGetResponse)
        self.assertNotIn(self.guid13, sinceGetResponse)
        self.assertNotIn(self.guid12, sinceGetResponse)
        self.assertNotIn(self.guid11, sinceGetResponse)
        self.assertNotIn(self.guid10, sinceGetResponse)
        self.assertNotIn(self.guid9, sinceGetResponse)
        self.assertNotIn(self.guid8, sinceGetResponse)
        self.assertNotIn(self.guid7, sinceGetResponse)
        self.assertNotIn(self.guid6, sinceGetResponse)
        self.assertNotIn(self.guid5, sinceGetResponse)
        self.assertNotIn(self.guid4, sinceGetResponse)
        self.assertNotIn(self.guid3, sinceGetResponse)
        self.assertNotIn(self.guid2, sinceGetResponse)
        self.assertNotIn(self.guid1, sinceGetResponse)                
        self.assertNotIn(self.guid25, sinceGetResponse)
        self.assertNotIn('more', sinceGetResponse)


    def test_limit_same_as_server_limit(self):
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime, "limit":10})
        resp_json = json.loads(sinceGetResponse.content)

        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertEqual(len(resp_json['statements']), 10)

        self.assertContains(sinceGetResponse, self.guid24)
        self.assertContains(sinceGetResponse, self.guid23)                
        self.assertContains(sinceGetResponse, self.guid22)
        self.assertContains(sinceGetResponse, self.guid21)
        self.assertContains(sinceGetResponse, self.guid20)                
        self.assertContains(sinceGetResponse, self.guid19)        
        self.assertContains(sinceGetResponse, self.guid18)
        self.assertContains(sinceGetResponse, self.guid17)    
        self.assertContains(sinceGetResponse, self.guid16)
        self.assertContains(sinceGetResponse, self.guid15)    

        self.assertNotIn(self.guid14, sinceGetResponse)
        self.assertNotIn(self.guid13, sinceGetResponse)
        self.assertNotIn(self.guid12, sinceGetResponse)
        self.assertNotIn(self.guid11, sinceGetResponse)
        self.assertNotIn(self.guid10, sinceGetResponse)
        self.assertNotIn(self.guid9, sinceGetResponse)
        self.assertNotIn(self.guid8, sinceGetResponse)
        self.assertNotIn(self.guid7, sinceGetResponse)
        self.assertNotIn(self.guid6, sinceGetResponse)
        self.assertNotIn(self.guid5, sinceGetResponse)
        self.assertNotIn(self.guid4, sinceGetResponse)
        self.assertNotIn(self.guid3, sinceGetResponse)
        self.assertNotIn(self.guid2, sinceGetResponse)
        self.assertNotIn(self.guid1, sinceGetResponse)                
        self.assertNotIn(self.guid25, sinceGetResponse)
        self.assertNotIn('more', sinceGetResponse)    

    def test_limit_more_than_server_limit(self):
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime, "limit":12})
        resp_json = json.loads(sinceGetResponse.content)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertEqual(len(resp_json['statements']), 10)        
        self.assertContains(sinceGetResponse, self.guid24)
        self.assertContains(sinceGetResponse, self.guid23)                
        self.assertContains(sinceGetResponse, self.guid22)
        self.assertContains(sinceGetResponse, self.guid21)
        self.assertContains(sinceGetResponse, self.guid20)                
        self.assertContains(sinceGetResponse, self.guid19)        
        self.assertContains(sinceGetResponse, self.guid18)
        self.assertContains(sinceGetResponse, self.guid17)    
        self.assertContains(sinceGetResponse, self.guid16)
        self.assertContains(sinceGetResponse, self.guid15)    

        self.assertNotIn(self.guid14, sinceGetResponse)
        self.assertNotIn(self.guid13, sinceGetResponse)
        self.assertNotIn(self.guid12, sinceGetResponse)
        self.assertNotIn(self.guid11, sinceGetResponse)
        self.assertNotIn(self.guid10, sinceGetResponse)
        self.assertNotIn(self.guid9, sinceGetResponse)
        self.assertNotIn(self.guid8, sinceGetResponse)
        self.assertNotIn(self.guid7, sinceGetResponse)
        self.assertNotIn(self.guid6, sinceGetResponse)
        self.assertNotIn(self.guid5, sinceGetResponse)
        self.assertNotIn(self.guid4, sinceGetResponse)
        self.assertNotIn(self.guid3, sinceGetResponse)
        self.assertNotIn(self.guid2, sinceGetResponse)
        self.assertNotIn(self.guid1, sinceGetResponse)                
        self.assertNotIn(self.guid25, sinceGetResponse)

        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))
        self.assertEqual(moreURLGet.status_code, 200)
        self.assertContains(moreURLGet, self.guid14)
        self.assertContains(moreURLGet, self.guid13)

        self.assertNotIn(self.guid24, moreURLGet)
        self.assertNotIn(self.guid23, moreURLGet)
        self.assertNotIn(self.guid22, moreURLGet)
        self.assertNotIn(self.guid21, moreURLGet)
        self.assertNotIn(self.guid20, moreURLGet)
        self.assertNotIn(self.guid19, moreURLGet)
        self.assertNotIn(self.guid18, moreURLGet)
        self.assertNotIn(self.guid17, moreURLGet)
        self.assertNotIn(self.guid16, moreURLGet)
        self.assertNotIn(self.guid15, moreURLGet)
        self.assertNotIn(self.guid12, moreURLGet)
        self.assertNotIn(self.guid11, moreURLGet)
        self.assertNotIn(self.guid10, moreURLGet)
        self.assertNotIn(self.guid9, moreURLGet)
        self.assertNotIn(self.guid8, moreURLGet)
        self.assertNotIn(self.guid7, moreURLGet)
        self.assertNotIn(self.guid6, moreURLGet)
        self.assertNotIn(self.guid5, moreURLGet)
        self.assertNotIn(self.guid4, moreURLGet)
        self.assertNotIn(self.guid3, moreURLGet)
        self.assertNotIn(self.guid2, moreURLGet)
        self.assertNotIn(self.guid1, moreURLGet)        
        self.assertNotIn(self.guid25, moreURLGet)


    def test_two_pages_full_third_not_full_more_stmts_multiple_hits(self):
        # Make initial complex get so 'more' will be required
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime})
        resp_json = json.loads(sinceGetResponse.content)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertContains(sinceGetResponse, self.guid24)
        self.assertContains(sinceGetResponse, self.guid23)                
        self.assertContains(sinceGetResponse, self.guid22)
        self.assertContains(sinceGetResponse, self.guid21)
        self.assertContains(sinceGetResponse, self.guid20)                
        self.assertContains(sinceGetResponse, self.guid19)        
        self.assertContains(sinceGetResponse, self.guid18)
        self.assertContains(sinceGetResponse, self.guid17)                
        self.assertContains(sinceGetResponse, self.guid16)
        self.assertContains(sinceGetResponse, self.guid15)

        self.assertNotIn(self.guid14, sinceGetResponse)
        self.assertNotIn(self.guid13, sinceGetResponse)
        self.assertNotIn(self.guid12, sinceGetResponse)
        self.assertNotIn(self.guid11, sinceGetResponse)
        self.assertNotIn(self.guid10, sinceGetResponse)
        self.assertNotIn(self.guid9, sinceGetResponse)
        self.assertNotIn(self.guid8, sinceGetResponse)
        self.assertNotIn(self.guid7, sinceGetResponse)
        self.assertNotIn(self.guid6, sinceGetResponse)
        self.assertNotIn(self.guid5, sinceGetResponse)
        self.assertNotIn(self.guid4, sinceGetResponse)
        self.assertNotIn(self.guid3, sinceGetResponse)
        self.assertNotIn(self.guid2, sinceGetResponse)
        self.assertNotIn(self.guid1, sinceGetResponse)        
        self.assertNotIn(self.guid25, sinceGetResponse)

        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))
        more_json = json.loads(moreURLGet.content)
        more_resp_url = more_json['more']
        more_resp_id = more_resp_url[-32:]

        self.assertEqual(moreURLGet.status_code, 200)
        self.assertContains(moreURLGet, self.guid14)
        self.assertContains(moreURLGet, self.guid13)                
        self.assertContains(moreURLGet, self.guid12)
        self.assertContains(moreURLGet, self.guid11)
        self.assertContains(moreURLGet, self.guid10)                
        self.assertContains(moreURLGet, self.guid9)        
        self.assertContains(moreURLGet, self.guid8)
        self.assertContains(moreURLGet, self.guid7)                
        self.assertContains(moreURLGet, self.guid6)
        self.assertContains(moreURLGet, self.guid5)

        self.assertNotIn(self.guid24, moreURLGet)
        self.assertNotIn(self.guid23, moreURLGet)
        self.assertNotIn(self.guid22, moreURLGet)
        self.assertNotIn(self.guid21, moreURLGet)
        self.assertNotIn(self.guid20, moreURLGet)
        self.assertNotIn(self.guid19, moreURLGet)
        self.assertNotIn(self.guid18, moreURLGet)
        self.assertNotIn(self.guid17, moreURLGet)
        self.assertNotIn(self.guid16, moreURLGet)
        self.assertNotIn(self.guid15, moreURLGet)
        self.assertNotIn(self.guid4, moreURLGet)
        self.assertNotIn(self.guid3, moreURLGet)
        self.assertNotIn(self.guid2, moreURLGet)
        self.assertNotIn(self.guid1, moreURLGet)        
        self.assertNotIn(self.guid25, moreURLGet)


        more2URLGet = self.client.get(reverse(views.statements_more, kwargs={'more_id':more_resp_id}))
        self.assertEqual(more2URLGet.status_code, 200)
        self.assertContains(more2URLGet, self.guid4)
        self.assertContains(more2URLGet, self.guid3)                
        self.assertContains(more2URLGet, self.guid2)
        self.assertContains(more2URLGet, self.guid1)

        self.assertNotIn(self.guid25, more2URLGet)
        self.assertNotIn(self.guid24, more2URLGet)
        self.assertNotIn(self.guid23, more2URLGet)
        self.assertNotIn(self.guid22, more2URLGet)
        self.assertNotIn(self.guid21, more2URLGet)
        self.assertNotIn(self.guid20, more2URLGet)
        self.assertNotIn(self.guid19, more2URLGet)
        self.assertNotIn(self.guid18, more2URLGet)
        self.assertNotIn(self.guid17, more2URLGet)
        self.assertNotIn(self.guid16, more2URLGet)
        self.assertNotIn(self.guid15, more2URLGet)
        self.assertNotIn(self.guid14, more2URLGet)
        self.assertNotIn(self.guid13, more2URLGet)
        self.assertNotIn(self.guid12, more2URLGet)
        self.assertNotIn(self.guid11, more2URLGet)        
        self.assertNotIn(self.guid10, more2URLGet)
        self.assertNotIn(self.guid9, more2URLGet)
        self.assertNotIn(self.guid8, more2URLGet)
        self.assertNotIn(self.guid7, more2URLGet)
        self.assertNotIn(self.guid6, more2URLGet)
        self.assertNotIn(self.guid5, more2URLGet)        

        # Simulate user clicking returned 'more' URL
        anotherMoreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}))
        another_more_json = json.loads(anotherMoreURLGet.content)
        another_more_resp_url = another_more_json['more']
        another_more_resp_id = another_more_resp_url[-32:]

        self.assertEqual(anotherMoreURLGet.status_code, 200)
        self.assertContains(anotherMoreURLGet, self.guid14)
        self.assertContains(anotherMoreURLGet, self.guid13)                
        self.assertContains(anotherMoreURLGet, self.guid12)
        self.assertContains(anotherMoreURLGet, self.guid11)
        self.assertContains(anotherMoreURLGet, self.guid10)                
        self.assertContains(anotherMoreURLGet, self.guid9)        
        self.assertContains(anotherMoreURLGet, self.guid8)
        self.assertContains(anotherMoreURLGet, self.guid7)                
        self.assertContains(anotherMoreURLGet, self.guid6)
        self.assertContains(anotherMoreURLGet, self.guid5)

        self.assertNotIn(self.guid24, anotherMoreURLGet)
        self.assertNotIn(self.guid23, anotherMoreURLGet)
        self.assertNotIn(self.guid22, anotherMoreURLGet)
        self.assertNotIn(self.guid21, anotherMoreURLGet)
        self.assertNotIn(self.guid20, anotherMoreURLGet)
        self.assertNotIn(self.guid19, anotherMoreURLGet)
        self.assertNotIn(self.guid18, anotherMoreURLGet)
        self.assertNotIn(self.guid17, anotherMoreURLGet)
        self.assertNotIn(self.guid16, anotherMoreURLGet)
        self.assertNotIn(self.guid15, anotherMoreURLGet)
        self.assertNotIn(self.guid4, anotherMoreURLGet)
        self.assertNotIn(self.guid3, anotherMoreURLGet)
        self.assertNotIn(self.guid2, anotherMoreURLGet)
        self.assertNotIn(self.guid1, anotherMoreURLGet)        
        self.assertNotIn(self.guid25, anotherMoreURLGet)

        # Simulate user clicking returned 'more' URL
        anotherMore2URLGet = self.client.get(reverse(views.statements_more, kwargs={'more_id':another_more_resp_id}))
        self.assertEqual(anotherMore2URLGet.status_code, 200)
        self.assertContains(anotherMore2URLGet, self.guid4)
        self.assertContains(anotherMore2URLGet, self.guid3)                
        self.assertContains(anotherMore2URLGet, self.guid2)
        self.assertContains(anotherMore2URLGet, self.guid1)

        self.assertNotIn(self.guid25, anotherMore2URLGet)
        self.assertNotIn(self.guid24, anotherMore2URLGet)
        self.assertNotIn(self.guid23, anotherMore2URLGet)
        self.assertNotIn(self.guid22, anotherMore2URLGet)
        self.assertNotIn(self.guid21, anotherMore2URLGet)
        self.assertNotIn(self.guid20, anotherMore2URLGet)
        self.assertNotIn(self.guid19, anotherMore2URLGet)
        self.assertNotIn(self.guid18, anotherMore2URLGet)
        self.assertNotIn(self.guid17, anotherMore2URLGet)
        self.assertNotIn(self.guid16, anotherMore2URLGet)
        self.assertNotIn(self.guid15, anotherMore2URLGet)
        self.assertNotIn(self.guid14, anotherMore2URLGet)
        self.assertNotIn(self.guid13, anotherMore2URLGet)
        self.assertNotIn(self.guid12, anotherMore2URLGet)
        self.assertNotIn(self.guid11, anotherMore2URLGet)        
        self.assertNotIn(self.guid10, anotherMore2URLGet)
        self.assertNotIn(self.guid9, anotherMore2URLGet)
        self.assertNotIn(self.guid8, anotherMore2URLGet)
        self.assertNotIn(self.guid7, anotherMore2URLGet)
        self.assertNotIn(self.guid6, anotherMore2URLGet)
        self.assertNotIn(self.guid5, anotherMore2URLGet)        
    

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


