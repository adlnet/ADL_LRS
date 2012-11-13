from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import views, models
import json
import base64
import uuid
from datetime import datetime, timedelta
from django.utils.timezone import utc
from lrs.objects import Activity
import time
import pdb
from lrs.util import retrieve_statement
from django.conf import settings

class StatementsMoreTests(TestCase):
    settings.SERVER_STMT_LIMIT=10

    def setUp(self):


        self.username = "auth1"
        self.email = "auth1@example.com"
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
        # Context guids
        self.cguid1 = str(uuid.uuid4())
        self.cguid2 = str(uuid.uuid4())    
        self.cguid3 = str(uuid.uuid4())
        self.cguid4 = str(uuid.uuid4())
        self.cguid5 = str(uuid.uuid4())
        self.mytime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())
        stmt_list = []

        self.existStmt1 = json.dumps({"statement_id":self.guid1,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "verb":{"id":"verb/attempted",
            "display":{"en-US":"attempted", 'en-GB':"altattempted"}},"object": {'objectType': 'Activity',
            'id':'foogie','definition': {'name': {'en-US':'testname2', 'en-GB':'altname'},
            'description': {'en-US':'testdesc2','en-GB':'altdesc'}, 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answer'],'extensions': {'key1': 'value1',
            'key2': 'value2','key3': 'value3'}}}, "result": {'score':{'scaled':.85}, 'completion': True, 'success': True,
            'response': 'kicked','duration': self.mytime, 'extensions':{'key1': 'value1', 'key2':'value2'}},
            'context':{'registration': self.cguid1, 'contextActivities': {'other': {'id': 'NewActivityID2'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey1': 'cval1',
            'ckey2': 'cval2'}}, 'authority':{'objectType':'Agent','name':'auth1','mbox':'auth1@example.com'}})        
        stmt_list.append(self.existStmt1)

        self.existStmt2 = json.dumps({"statement_id":self.guid2,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "verb":{"id":"verb/created",
            "display":{"en-US":"created", 'en-GB':"altcreated"}}, "object": {'objectType': 'Activity',
            'id':'foogie','definition': {'name': {'en-US':'testname3'},'description': {'en-US':'testdesc3'},
            'type': 'cmi.interaction','interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key11': 'value11', 'key22': 'value22','key33': 'value33'}}}, 
            "result": {'score':{'scaled':.75}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid2, 'contextActivities': {'other': {'id': 'NewActivityID24'}},
            'revision': 'food', 'platform':'bard','language': 'en-US', 'extensions':{'ckey11': 'cval11',
            'ckey22': 'cval22'}}, 'authority':{'objectType':'Agent','name':'auth1','mbox':'auth1@example.com'}})        
        stmt_list.append(self.existStmt2)

        self.existStmt3 = json.dumps({"statement_id":self.guid3,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "verb":{"id":"verb/created",
            "display":{"en-US":"created", 'en-GB':"altcreated"}}, "object": {'objectType': 'Activity',
            'id':'foogals','definition': {'name': {'en-US':'testname3'},'description': {'en-US':'testdesc3'},
            'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
            "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid3, 'contextActivities': {'other': {'id': 'NewActivityID23'}},
            'revision': 'food', 'platform':'bard','language': 'en-US','instructor':{'name':['bill'],
            'mbox':['bill@bill.com']} , 'extensions':{'ckey111': 'cval111',
            'ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':'auth1','mbox':'auth1@example.com'}})        
        stmt_list.append(self.existStmt3)

        self.existStmt4 = json.dumps({"statement_id":self.guid4,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "verb":{"id":"verb/created",
            "display":{"en-US":"created", 'en-GB':"altcreated"}}, "object": {'objectType': 'Activity', 'id':'foogal',
            'definition': {'name': {'en-US':'testname3'},'description': {'en-US':'testdesc3'}, 'type': 'cmi.interaction',
            'interactionType': 'fill-in','correctResponsesPattern': ['answers'],
            'extensions': {'key111': 'value111', 'key222': 'value222','key333': 'value333'}}}, 
            "result": {'score':{'scaled':.79}, 'completion': True, 'success': True, 'response': 'shouted',
            'duration': self.mytime, 'extensions':{'dkey1': 'dvalue1', 'dkey2':'dvalue2'}},
            'context':{'registration': self.cguid4, 'contextActivities': {'other': {'id': 'NewActivityID22'}},
            'revision': 'food', 'platform':'bard','language': 'en-US','instructor':{'name':['bill'],
            'mbox':['bill@bill.com']}, 'extensions':{'ckey111': 'cval111',
            'ckey222': 'cval222'}}, 'authority':{'objectType':'Agent','name':'auth1','mbox':'auth1@example.com'}})
        stmt_list.append(self.existStmt4)

        self.existStmt5 = json.dumps({"statement_id":self.guid5,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon1',
            'mbox':'jon1@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt5)

        self.existStmt6 = json.dumps({"statement_id":self.guid6,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon2',
            'mbox':'jon2@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt6)

        self.existStmt7 = json.dumps({"statement_id":self.guid7,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon3',
            'mbox':'jon3@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt7)

        self.existStmt8 = json.dumps({"statement_id":self.guid8,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon4',
            'mbox':'jon4@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt8)

        self.existStmt9 = json.dumps({"statement_id":self.guid9,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon5',
            'mbox':'jon5@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt9)

        self.existStmt10 = json.dumps({"statement_id":self.guid10,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon33',
            'mbox':'jon33@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})       
        stmt_list.append(self.existStmt10)

        self.existStmt11 = json.dumps({"statement_id":self.guid11,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon6',
            'mbox':'jon6@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt11)

        self.existStmt12 = json.dumps({"statement_id":self.guid12,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon7',
            'mbox':'jon7@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt12)

        self.existStmt13 = json.dumps({"statement_id":self.guid13,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon8',
            'mbox':'jon8@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt13)

        self.existStmt14 = json.dumps({"statement_id":self.guid14,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon9',
            'mbox':'jon9@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt14)

        self.existStmt15 = json.dumps({"statement_id":self.guid15,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon10',
            'mbox':'jon10@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt15)

        self.existStmt16 = json.dumps({"statement_id":self.guid16,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon11',
            'mbox':'jon11@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt16)

        self.existStmt17 = json.dumps({"statement_id":self.guid17,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon12',
            'mbox':'jon12@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt17)

        self.existStmt18 = json.dumps({"statement_id":self.guid18,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon13',
            'mbox':'jon13@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt18)

        self.existStmt19 = json.dumps({"statement_id":self.guid19,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon14',
            'mbox':'jon14@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt19)

        self.existStmt20 = json.dumps({"statement_id":self.guid20,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon15',
            'mbox':'jon15@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})       
        stmt_list.append(self.existStmt20)

        self.existStmt21 = json.dumps({"statement_id":self.guid21,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon16',
            'mbox':'jon16@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt21)

        self.existStmt22 = json.dumps({"statement_id":self.guid22,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon17',
            'mbox':'jon17@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt22)

        self.existStmt23 = json.dumps({"statement_id":self.guid23,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon18',
            'mbox':'jon18@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt23)

        self.existStmt24 = json.dumps({"statement_id":self.guid24,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon19',
            'mbox':'jon19@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt24)

        self.existStmt25 = json.dumps({"statement_id":self.guid25,"actor":{"objectType":"Agent","mbox":"s@s.com"},
            "object":{'objectType':'Agent','name':'jon20',
            'mbox':'jon20@jon.com'},"verb":{"id":"verb/passed",
            "display":{"en-US":"passed", 'en-GB':"altpassed"}}})
        stmt_list.append(self.existStmt25)



        # Post statements
        post_statements = self.client.post(reverse(views.statements), json.dumps(stmt_list),content_type="application/json",HTTP_AUTHORIZATION=self.auth, X_Experience_API_Version="0.95")
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=1)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid1).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=2)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid2).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=3)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid3).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=4)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid4).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=5)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid5).update(stored=time)

        self.secondTime = str((datetime.utcnow()+timedelta(seconds=6)).replace(tzinfo=utc).isoformat())

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=7)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid6).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=8)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid7).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=9)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid8).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=10)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid9).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=11)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid10).update(stored=time)

        self.thirdTime = str((datetime.utcnow()+timedelta(seconds=12)).replace(tzinfo=utc).isoformat())

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=13)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid11).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=14)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid12).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=15)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid13).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=16)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid14).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=17)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid15).update(stored=time)

        self.fourthTime = str((datetime.utcnow()+timedelta(seconds=18)).replace(tzinfo=utc).isoformat())

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=19)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid16).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=20)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid17).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=21)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid18).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=22)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid19).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=23)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid20).update(stored=time)

        self.fifthTime = str((datetime.utcnow()+timedelta(seconds=24)).replace(tzinfo=utc).isoformat())
 
        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=25)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid21).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=26)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid22).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=27)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid23).update(stored=time)

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=28)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid24).update(stored=time)

        self.sixthTime = str((datetime.utcnow()+timedelta(seconds=29)).replace(tzinfo=utc).isoformat())

        time = retrieve_statement.convertToUTC(str((datetime.utcnow()+timedelta(seconds=30)).replace(tzinfo=utc).isoformat()))
        stmt = models.statement.objects.filter(statement_id=self.guid25).update(stored=time)


    def test_unknown_more_id_url(self):
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}), X_Experience_API_Version="0.95")
        self.assertContains(moreURLGet, 'List does not exist - may have expired after 24 hours')

    def test_not_full_page_stmts(self):
        sincePostResponse = self.client.post(reverse(views.statements), {"until":self.secondTime},content_type="application/x-www-form-urlencoded", X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)

        self.assertEqual(sincePostResponse.status_code, 200)
        rsp = sincePostResponse.content
        self.assertIn(self.guid5, rsp)
        self.assertIn(self.guid4, rsp)
        self.assertIn(self.guid3, rsp)
        self.assertIn(self.guid2, rsp)
        self.assertIn(self.guid1, rsp)

        self.assertNotIn(self.guid25, rsp)
        self.assertNotIn(self.guid24, rsp)
        self.assertNotIn(self.guid23, rsp)
        self.assertNotIn(self.guid22, rsp)
        self.assertNotIn(self.guid21, rsp)
        self.assertNotIn(self.guid20, rsp)
        self.assertNotIn(self.guid19, rsp)
        self.assertNotIn(self.guid18, rsp)
        self.assertNotIn(self.guid17, rsp)
        self.assertNotIn(self.guid16, rsp)
        self.assertNotIn(self.guid15, rsp)
        self.assertNotIn(self.guid14, rsp)
        self.assertNotIn(self.guid13, rsp)
        self.assertNotIn(self.guid12, rsp)
        self.assertNotIn(self.guid11, rsp)
        self.assertNotIn(self.guid10, rsp)
        self.assertNotIn(self.guid9, rsp)
        self.assertNotIn(self.guid7, rsp)
        self.assertNotIn(self.guid8, rsp)
        self.assertNotIn(self.guid6, rsp)

    def test_single_full_page_stmts(self):


        sincePostResponse = self.client.post(reverse(views.statements),
            {"until":self.thirdTime},
            content_type="application/x-www-form-urlencoded", X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(sincePostResponse.status_code, 200)
        rsp = sincePostResponse.content
        self.assertIn(self.guid10, rsp)
        self.assertIn(self.guid9, rsp)
        self.assertIn(self.guid8, rsp)
        self.assertIn(self.guid7, rsp)
        self.assertIn(self.guid6, rsp)
        self.assertIn(self.guid5, rsp)
        self.assertIn(self.guid4, rsp)
        self.assertIn(self.guid3, rsp)
        self.assertIn(self.guid2, rsp)
        self.assertIn(self.guid1, rsp)

        self.assertNotIn(self.guid25, rsp)
        self.assertNotIn(self.guid24, rsp)
        self.assertNotIn(self.guid23, rsp)
        self.assertNotIn(self.guid22, rsp)
        self.assertNotIn(self.guid21, rsp)
        self.assertNotIn(self.guid20, rsp)
        self.assertNotIn(self.guid19, rsp)
        self.assertNotIn(self.guid18, rsp)
        self.assertNotIn(self.guid17, rsp)
        self.assertNotIn(self.guid16, rsp)
        self.assertNotIn(self.guid15, rsp)
        self.assertNotIn(self.guid14, rsp)
        self.assertNotIn(self.guid13, rsp)
        self.assertNotIn(self.guid12, rsp)
        self.assertNotIn(self.guid11, rsp)

    def test_single_full_second_not_full_more_stmts_url(self):
        sincePostResponse = self.client.post(reverse(views.statements), {"until":self.fourthTime},content_type="application/x-www-form-urlencoded", X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(sincePostResponse.status_code, 200)
        rsp = sincePostResponse.content
        resp_json = json.loads(rsp)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertIn(self.guid15, rsp)
        self.assertIn(self.guid14, rsp)
        self.assertIn(self.guid13, rsp)
        self.assertIn(self.guid12, rsp)
        self.assertIn(self.guid11, rsp)
        self.assertIn(self.guid10, rsp)
        self.assertIn(self.guid9, rsp)
        self.assertIn(self.guid8, rsp)
        self.assertIn(self.guid7, rsp)
        self.assertIn(self.guid6, rsp)

        self.assertNotIn(self.guid25, rsp)
        self.assertNotIn(self.guid24, rsp)
        self.assertNotIn(self.guid23, rsp)
        self.assertNotIn(self.guid22, rsp)
        self.assertNotIn(self.guid21, rsp)        
        self.assertNotIn(self.guid20, rsp)
        self.assertNotIn(self.guid19, rsp)
        self.assertNotIn(self.guid18, rsp)
        self.assertNotIn(self.guid17, rsp)
        self.assertNotIn(self.guid16, rsp)
        self.assertNotIn(self.guid5, rsp)
        self.assertNotIn(self.guid4, rsp)
        self.assertNotIn(self.guid3, rsp)
        self.assertNotIn(self.guid2, rsp)
        self.assertNotIn(self.guid1, rsp)

        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}), X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)

        self.assertEqual(moreURLGet.status_code, 200)
        more_rsp = moreURLGet.content
        self.assertIn(self.guid5, more_rsp)
        self.assertIn(self.guid4, more_rsp)
        self.assertIn(self.guid3, more_rsp)
        self.assertIn(self.guid2, more_rsp)
        self.assertIn(self.guid1, more_rsp)

        self.assertNotIn(self.guid24, more_rsp)
        self.assertNotIn(self.guid23, more_rsp)
        self.assertNotIn(self.guid22, more_rsp)
        self.assertNotIn(self.guid21, more_rsp)
        self.assertNotIn(self.guid20, more_rsp)
        self.assertNotIn(self.guid19, more_rsp)
        self.assertNotIn(self.guid18, more_rsp)
        self.assertNotIn(self.guid17, more_rsp)
        self.assertNotIn(self.guid16, more_rsp)
        self.assertNotIn(self.guid15, more_rsp)
        self.assertNotIn(self.guid14, more_rsp)
        self.assertNotIn(self.guid13, more_rsp)
        self.assertNotIn(self.guid12, more_rsp)
        self.assertNotIn(self.guid11, more_rsp)
        self.assertNotIn(self.guid10, more_rsp)
        self.assertNotIn(self.guid9, more_rsp)
        self.assertNotIn(self.guid8, more_rsp)
        self.assertNotIn(self.guid7, more_rsp)
        self.assertNotIn(self.guid6, more_rsp)        
        self.assertNotIn(self.guid25, more_rsp)

    def test_two_pages_full_more_stmts_url(self):
        sincePostResponse = self.client.post(reverse(views.statements), {"until":self.fifthTime},content_type="application/x-www-form-urlencoded", X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(sincePostResponse.status_code, 200)
        rsp = sincePostResponse.content
        resp_json = json.loads(rsp)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertIn(self.guid20, rsp)
        self.assertIn(self.guid19, rsp)
        self.assertIn(self.guid18, rsp)
        self.assertIn(self.guid17, rsp)
        self.assertIn(self.guid16, rsp)
        self.assertIn(self.guid15, rsp)
        self.assertIn(self.guid14, rsp)
        self.assertIn(self.guid13, rsp)
        self.assertIn(self.guid12, rsp)
        self.assertIn(self.guid11, rsp)

        self.assertNotIn(self.guid25, rsp)
        self.assertNotIn(self.guid24, rsp)
        self.assertNotIn(self.guid23, rsp)
        self.assertNotIn(self.guid22, rsp)
        self.assertNotIn(self.guid21, rsp)        
        self.assertNotIn(self.guid10, rsp)
        self.assertNotIn(self.guid9, rsp)
        self.assertNotIn(self.guid8, rsp)
        self.assertNotIn(self.guid7, rsp)
        self.assertNotIn(self.guid6, rsp)
        self.assertNotIn(self.guid5, rsp)
        self.assertNotIn(self.guid4, rsp)
        self.assertNotIn(self.guid3, rsp)
        self.assertNotIn(self.guid2, rsp)
        self.assertNotIn(self.guid1, rsp)

        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}), X_Experience_API_Version="0.95")

        self.assertEqual(moreURLGet.status_code, 200)
        more_rsp = moreURLGet.content
        self.assertIn(self.guid10, more_rsp)
        self.assertIn(self.guid9, more_rsp)
        self.assertIn(self.guid8, more_rsp)
        self.assertIn(self.guid7, more_rsp)
        self.assertIn(self.guid6, more_rsp)
        self.assertIn(self.guid5, more_rsp)
        self.assertIn(self.guid4, more_rsp)
        self.assertIn(self.guid3, more_rsp)
        self.assertIn(self.guid2, more_rsp)
        self.assertIn(self.guid1, more_rsp)

        self.assertNotIn(self.guid24, more_rsp)
        self.assertNotIn(self.guid23, more_rsp)
        self.assertNotIn(self.guid22, more_rsp)
        self.assertNotIn(self.guid21, more_rsp)
        self.assertNotIn(self.guid20, more_rsp)
        self.assertNotIn(self.guid19, more_rsp)
        self.assertNotIn(self.guid18, more_rsp)
        self.assertNotIn(self.guid17, more_rsp)
        self.assertNotIn(self.guid16, more_rsp)
        self.assertNotIn(self.guid15, more_rsp)
        self.assertNotIn(self.guid14, more_rsp)
        self.assertNotIn(self.guid13, more_rsp)
        self.assertNotIn(self.guid12, more_rsp)
        self.assertNotIn(self.guid11, more_rsp)       
        self.assertNotIn(self.guid25, more_rsp)

    def test_two_pages_full_third_not_full_more_stmts_url(self):
        # Make initial complex get so 'more' will be required
        pdb.set_trace()
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime}, X_Experience_API_Version="0.95", HTTP_AUTHORIZATION=self.auth)
        rsp = sinceGetResponse.content
        resp_json = json.loads(rsp)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]
        print 'first more ID just created:' + str(resp_id)
        self.assertEqual(sinceGetResponse.status_code, 200)
        self.assertIn(self.guid24, rsp)
        self.assertIn(self.guid23, rsp)
        self.assertIn(self.guid22, rsp)
        self.assertIn(self.guid21, rsp)
        self.assertIn(self.guid20, rsp)
        self.assertIn(self.guid19, rsp)
        self.assertIn(self.guid18, rsp)
        self.assertIn(self.guid17, rsp)
        self.assertIn(self.guid16, rsp)
        self.assertIn(self.guid15, rsp)

        self.assertNotIn(self.guid14, rsp)
        self.assertNotIn(self.guid13, rsp)
        self.assertNotIn(self.guid12, rsp)
        self.assertNotIn(self.guid11, rsp)
        self.assertNotIn(self.guid10, rsp)
        self.assertNotIn(self.guid9, rsp)
        self.assertNotIn(self.guid8, rsp)
        self.assertNotIn(self.guid7, rsp)
        self.assertNotIn(self.guid6, rsp)
        self.assertNotIn(self.guid5, rsp)
        self.assertNotIn(self.guid4, rsp)
        self.assertNotIn(self.guid3, rsp)
        self.assertNotIn(self.guid2, rsp)
        self.assertNotIn(self.guid1, rsp)        
        self.assertNotIn(self.guid25, rsp)

        pdb.set_trace()
        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}), X_Experience_API_Version="0.95")
        more_rsp = moreURLGet.content
        more_json = json.loads(rsp)
        more_resp_url = more_json['more']
        more_resp_id = more_resp_url[-32:]
        print "second more ID just created: " + str(more_resp_id)
        self.assertEqual(moreURLGet.status_code, 200)
        self.assertIn(self.guid14, more_rsp)
        self.assertIn(self.guid13, more_rsp)
        self.assertIn(self.guid12, more_rsp)
        self.assertIn(self.guid11, more_rsp)
        self.assertIn(self.guid10, more_rsp)
        self.assertIn(self.guid9, more_rsp)
        self.assertIn(self.guid8, more_rsp)
        self.assertIn(self.guid7, more_rsp)
        self.assertIn(self.guid6, more_rsp)
        self.assertIn(self.guid5, more_rsp)

        self.assertNotIn(self.guid24, more_rsp)
        self.assertNotIn(self.guid23, more_rsp)
        self.assertNotIn(self.guid22, more_rsp)
        self.assertNotIn(self.guid21, more_rsp)
        self.assertNotIn(self.guid20, more_rsp)
        self.assertNotIn(self.guid19, more_rsp)
        self.assertNotIn(self.guid18, more_rsp)
        self.assertNotIn(self.guid17, more_rsp)
        self.assertNotIn(self.guid16, more_rsp)
        self.assertNotIn(self.guid15, more_rsp)
        self.assertNotIn(self.guid4, more_rsp)
        self.assertNotIn(self.guid3, more_rsp)
        self.assertNotIn(self.guid2, more_rsp)
        self.assertNotIn(self.guid1, more_rsp)        
        self.assertNotIn(self.guid25, more_rsp)

        pdb.set_trace()
        more2URLGet = self.client.get(reverse(views.statements_more, kwargs={'more_id':more_resp_id}), X_Experience_API_Version="0.95")
        self.assertEqual(more2URLGet.status_code, 200)
        more2_rsp = more2URLGet.content

        self.assertIn(self.guid4, more2_rsp)
        self.assertIn(self.guid3, more2_rsp)
        self.assertIn(self.guid2, more2_rsp)
        self.assertIn(self.guid1, more2_rsp)

        self.assertNotIn(self.guid25, more2_rsp)
        self.assertNotIn(self.guid24, more2_rsp)
        self.assertNotIn(self.guid23, more2_rsp)
        self.assertNotIn(self.guid22, more2_rsp)
        self.assertNotIn(self.guid21, more2_rsp)
        self.assertNotIn(self.guid20, more2_rsp)
        self.assertNotIn(self.guid19, more2_rsp)
        self.assertNotIn(self.guid18, more2_rsp)
        self.assertNotIn(self.guid17, more2_rsp)
        self.assertNotIn(self.guid16, more2_rsp)
        self.assertNotIn(self.guid15, more2_rsp)
        self.assertNotIn(self.guid14, more2_rsp)
        self.assertNotIn(self.guid13, more2_rsp)
        self.assertNotIn(self.guid12, more2_rsp)
        self.assertNotIn(self.guid11, more2_rsp)        
        self.assertNotIn(self.guid10, more2_rsp)
        self.assertNotIn(self.guid9, more2_rsp)
        self.assertNotIn(self.guid8, more2_rsp)
        self.assertNotIn(self.guid7, more2_rsp)
        self.assertNotIn(self.guid6, more2_rsp)
        self.assertNotIn(self.guid5, more2_rsp)        
    
    def test_limit_less_than_server_limit(self):
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime, "limit":8}, X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(sinceGetResponse.status_code, 200)
        rsp = sinceGetResponse.content
        resp_json = json.loads(rsp)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertEqual(len(resp_json['statements']), 8)        

        self.assertIn(self.guid24, rsp)
        self.assertIn(self.guid23, rsp)                
        self.assertIn(self.guid22, rsp)
        self.assertIn(self.guid21, rsp)
        self.assertIn(self.guid20, rsp)                
        self.assertIn(self.guid19, rsp)        
        self.assertIn(self.guid18, rsp)
        self.assertIn(self.guid17, rsp)    

        self.assertNotIn(self.guid16, rsp)
        self.assertNotIn(self.guid15, rsp)
        self.assertNotIn(self.guid14, rsp)
        self.assertNotIn(self.guid13, rsp)
        self.assertNotIn(self.guid12, rsp)
        self.assertNotIn(self.guid11, rsp)
        self.assertNotIn(self.guid10, rsp)
        self.assertNotIn(self.guid9, rsp)
        self.assertNotIn(self.guid8, rsp)
        self.assertNotIn(self.guid7, rsp)
        self.assertNotIn(self.guid6, rsp)
        self.assertNotIn(self.guid5, rsp)
        self.assertNotIn(self.guid4, rsp)
        self.assertNotIn(self.guid3, rsp)
        self.assertNotIn(self.guid2, rsp)
        self.assertNotIn(self.guid1, rsp)                
        self.assertNotIn(self.guid25, rsp)

        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}), X_Experience_API_Version="0.95")
        self.assertEqual(moreURLGet.status_code, 200)
        more_rsp = moreURLGet.content
        more_json = json.loads(more_rsp)
        more_resp_url = more_json['more']
        more_resp_id = more_resp_url[-32:]

        self.assertIn(self.guid16, more_rsp)
        self.assertIn(self.guid15, more_rsp)
        self.assertIn(self.guid14, more_rsp)
        self.assertIn(self.guid13, more_rsp)
        self.assertIn(self.guid12, more_rsp)
        self.assertIn(self.guid11, more_rsp)
        self.assertIn(self.guid10, more_rsp)
        self.assertIn(self.guid9, more_rsp)

        self.assertNotIn(self.guid24, more_rsp)
        self.assertNotIn(self.guid23, more_rsp)
        self.assertNotIn(self.guid22, more_rsp)
        self.assertNotIn(self.guid21, more_rsp)
        self.assertNotIn(self.guid20, more_rsp)
        self.assertNotIn(self.guid19, more_rsp)
        self.assertNotIn(self.guid18, more_rsp)
        self.assertNotIn(self.guid17, more_rsp)
        self.assertNotIn(self.guid8, more_rsp)
        self.assertNotIn(self.guid7, more_rsp)
        self.assertNotIn(self.guid6, more_rsp)
        self.assertNotIn(self.guid5, more_rsp)
        self.assertNotIn(self.guid4, more_rsp)
        self.assertNotIn(self.guid3, more_rsp)
        self.assertNotIn(self.guid2, more_rsp)
        self.assertNotIn(self.guid1, more_rsp)                
        self.assertNotIn(self.guid25, more_rsp)

        anotherURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':more_resp_id}), X_Experience_API_Version="0.95")
        self.assertEqual(anotherURLGet.status_code, 200)
        another_rsp = anotherURLGet.content

        self.assertIn(self.guid8, another_rsp)
        self.assertIn(self.guid7, another_rsp)
        self.assertIn(self.guid6, another_rsp)
        self.assertIn(self.guid5, another_rsp)
        self.assertIn(self.guid4, another_rsp)
        self.assertIn(self.guid3, another_rsp)
        self.assertIn(self.guid2, another_rsp)
        self.assertIn(self.guid1, another_rsp)

        self.assertNotIn(self.guid24, another_rsp)
        self.assertNotIn(self.guid23, another_rsp)
        self.assertNotIn(self.guid22, another_rsp)
        self.assertNotIn(self.guid21, another_rsp)
        self.assertNotIn(self.guid20, another_rsp)
        self.assertNotIn(self.guid19, another_rsp)
        self.assertNotIn(self.guid18, another_rsp)
        self.assertNotIn(self.guid17, another_rsp)
        self.assertNotIn(self.guid16, another_rsp)
        self.assertNotIn(self.guid15, another_rsp)
        self.assertNotIn(self.guid14, another_rsp)
        self.assertNotIn(self.guid13, another_rsp)
        self.assertNotIn(self.guid12, another_rsp)
        self.assertNotIn(self.guid11, another_rsp)
        self.assertNotIn(self.guid10, another_rsp)
        self.assertNotIn(self.guid9, another_rsp)                
        self.assertNotIn(self.guid25, another_rsp)


    def test_limit_same_as_server_limit(self):
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime, "limit":10}, X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(sinceGetResponse.status_code, 200)
        rsp = sinceGetResponse.content
        resp_json = json.loads(rsp)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertEqual(len(resp_json['statements']), 10)

        self.assertIn(self.guid24, rsp)
        self.assertIn(self.guid23, rsp)
        self.assertIn(self.guid22, rsp)
        self.assertIn(self.guid21, rsp)
        self.assertIn(self.guid20, rsp)
        self.assertIn(self.guid19, rsp)
        self.assertIn(self.guid18, rsp)
        self.assertIn(self.guid17, rsp)
        self.assertIn(self.guid16, rsp)
        self.assertIn(self.guid15, rsp)

        self.assertNotIn(self.guid14, rsp)
        self.assertNotIn(self.guid13, rsp)
        self.assertNotIn(self.guid12, rsp)
        self.assertNotIn(self.guid11, rsp)
        self.assertNotIn(self.guid10, rsp)
        self.assertNotIn(self.guid9, rsp)
        self.assertNotIn(self.guid8, rsp)
        self.assertNotIn(self.guid7, rsp)
        self.assertNotIn(self.guid6, rsp)
        self.assertNotIn(self.guid5, rsp)
        self.assertNotIn(self.guid4, rsp)
        self.assertNotIn(self.guid3, rsp)
        self.assertNotIn(self.guid2, rsp)
        self.assertNotIn(self.guid1, rsp)                
        self.assertNotIn(self.guid25, rsp)

        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}), X_Experience_API_Version="0.95")
        self.assertEqual(moreURLGet.status_code, 200)
        more_rsp = moreURLGet.content
        more_json = json.loads(more_rsp)
        more_resp_url = more_json['more']
        more_resp_id = more_resp_url[-32:]

        self.assertIn(self.guid14, more_rsp)
        self.assertIn(self.guid13, more_rsp)
        self.assertIn(self.guid12, more_rsp)
        self.assertIn(self.guid11, more_rsp)
        self.assertIn(self.guid10, more_rsp)
        self.assertIn(self.guid9, more_rsp)
        self.assertIn(self.guid8, more_rsp)
        self.assertIn(self.guid7, more_rsp)
        self.assertIn(self.guid6, more_rsp)
        self.assertIn(self.guid5, more_rsp)

        self.assertNotIn(self.guid24, more_rsp)
        self.assertNotIn(self.guid23, more_rsp)
        self.assertNotIn(self.guid22, more_rsp)
        self.assertNotIn(self.guid21, more_rsp)
        self.assertNotIn(self.guid20, more_rsp)
        self.assertNotIn(self.guid19, more_rsp)
        self.assertNotIn(self.guid18, more_rsp)
        self.assertNotIn(self.guid17, more_rsp)
        self.assertNotIn(self.guid16, more_rsp)
        self.assertNotIn(self.guid15, more_rsp)
        self.assertNotIn(self.guid4, more_rsp)
        self.assertNotIn(self.guid3, more_rsp)
        self.assertNotIn(self.guid2, more_rsp)
        self.assertNotIn(self.guid1, more_rsp)                
        self.assertNotIn(self.guid25, more_rsp)

        anotherURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':more_resp_id}), X_Experience_API_Version="0.95")
        self.assertEqual(anotherURLGet.status_code, 200)
        another_rsp = anotherURLGet.content

        self.assertIn(self.guid4, another_rsp)
        self.assertIn(self.guid3, another_rsp)
        self.assertIn(self.guid2, another_rsp)
        self.assertIn(self.guid1, another_rsp)

        self.assertNotIn(self.guid24, another_rsp)
        self.assertNotIn(self.guid23, another_rsp)
        self.assertNotIn(self.guid22, another_rsp)
        self.assertNotIn(self.guid21, another_rsp)
        self.assertNotIn(self.guid20, another_rsp)
        self.assertNotIn(self.guid19, another_rsp)
        self.assertNotIn(self.guid18, another_rsp)
        self.assertNotIn(self.guid17, another_rsp)
        self.assertNotIn(self.guid16, another_rsp)
        self.assertNotIn(self.guid15, another_rsp)
        self.assertNotIn(self.guid14, another_rsp)
        self.assertNotIn(self.guid13, another_rsp)
        self.assertNotIn(self.guid12, another_rsp)
        self.assertNotIn(self.guid11, another_rsp)
        self.assertNotIn(self.guid10, another_rsp)
        self.assertNotIn(self.guid9, another_rsp)                
        self.assertNotIn(self.guid8, another_rsp)
        self.assertNotIn(self.guid7, another_rsp)
        self.assertNotIn(self.guid6, another_rsp)
        self.assertNotIn(self.guid5, another_rsp)
        self.assertNotIn(self.guid25, another_rsp)    

    def test_limit_more_than_server_limit(self):
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime, "limit":12}, X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(sinceGetResponse.status_code, 200)
        rsp = sinceGetResponse.content
        resp_json = json.loads(rsp)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertEqual(len(resp_json['statements']), 10)        
        self.assertIn(self.guid24, rsp)
        self.assertIn(self.guid23, rsp)
        self.assertIn(self.guid22, rsp)
        self.assertIn(self.guid21, rsp)
        self.assertIn(self.guid20, rsp)
        self.assertIn(self.guid19, rsp)
        self.assertIn(self.guid18, rsp)
        self.assertIn(self.guid17, rsp)
        self.assertIn(self.guid16, rsp)
        self.assertIn(self.guid15, rsp)

        self.assertNotIn(self.guid14, rsp)
        self.assertNotIn(self.guid13, rsp)
        self.assertNotIn(self.guid12, rsp)
        self.assertNotIn(self.guid11, rsp)
        self.assertNotIn(self.guid10, rsp)
        self.assertNotIn(self.guid9, rsp)
        self.assertNotIn(self.guid8, rsp)
        self.assertNotIn(self.guid7, rsp)
        self.assertNotIn(self.guid6, rsp)
        self.assertNotIn(self.guid5, rsp)
        self.assertNotIn(self.guid4, rsp)
        self.assertNotIn(self.guid3, rsp)
        self.assertNotIn(self.guid2, rsp)
        self.assertNotIn(self.guid1, rsp)                
        self.assertNotIn(self.guid25, rsp)

        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}), X_Experience_API_Version="0.95")
        self.assertEqual(moreURLGet.status_code, 200)
        more_rsp = moreURLGet.content
        more_json = json.loads(more_rsp)
        more_resp_url = more_json['more']
        more_resp_id = more_resp_url[-32:]

        self.assertIn(self.guid14, more_rsp)
        self.assertIn(self.guid13, more_rsp)
        self.assertIn(self.guid12, more_rsp)
        self.assertIn(self.guid11, more_rsp)
        self.assertIn(self.guid10, more_rsp)
        self.assertIn(self.guid9, more_rsp)
        self.assertIn(self.guid8, more_rsp)
        self.assertIn(self.guid7, more_rsp)
        self.assertIn(self.guid6, more_rsp)
        self.assertIn(self.guid5, more_rsp)

        self.assertNotIn(self.guid24, more_rsp)
        self.assertNotIn(self.guid23, more_rsp)
        self.assertNotIn(self.guid22, more_rsp)
        self.assertNotIn(self.guid21, more_rsp)
        self.assertNotIn(self.guid20, more_rsp)
        self.assertNotIn(self.guid19, more_rsp)
        self.assertNotIn(self.guid18, more_rsp)
        self.assertNotIn(self.guid17, more_rsp)
        self.assertNotIn(self.guid16, more_rsp)
        self.assertNotIn(self.guid15, more_rsp)
        self.assertNotIn(self.guid4, more_rsp)
        self.assertNotIn(self.guid3, more_rsp)
        self.assertNotIn(self.guid2, more_rsp)
        self.assertNotIn(self.guid1, more_rsp)        
        self.assertNotIn(self.guid25, more_rsp)


        anotherURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':more_resp_id}), X_Experience_API_Version="0.95")
        self.assertEqual(anotherURLGet.status_code, 200)
        another_rsp = anotherURLGet.content

        self.assertIn(self.guid4, another_rsp)
        self.assertIn(self.guid3, another_rsp)
        self.assertIn(self.guid2, another_rsp)
        self.assertIn(self.guid1, another_rsp)

        self.assertNotIn(self.guid24, another_rsp)
        self.assertNotIn(self.guid23, another_rsp)
        self.assertNotIn(self.guid22, another_rsp)
        self.assertNotIn(self.guid21, another_rsp)
        self.assertNotIn(self.guid20, another_rsp)
        self.assertNotIn(self.guid19, another_rsp)
        self.assertNotIn(self.guid18, another_rsp)
        self.assertNotIn(self.guid17, another_rsp)
        self.assertNotIn(self.guid16, another_rsp)
        self.assertNotIn(self.guid15, another_rsp)
        self.assertNotIn(self.guid14, another_rsp)
        self.assertNotIn(self.guid13, another_rsp)
        self.assertNotIn(self.guid12, another_rsp)
        self.assertNotIn(self.guid11, another_rsp)
        self.assertNotIn(self.guid10, another_rsp)
        self.assertNotIn(self.guid9, another_rsp)                
        self.assertNotIn(self.guid8, another_rsp)
        self.assertNotIn(self.guid7, another_rsp)
        self.assertNotIn(self.guid6, another_rsp)
        self.assertNotIn(self.guid5, another_rsp)
        self.assertNotIn(self.guid25, another_rsp)

    def test_two_pages_full_third_not_full_more_stmts_multiple_hits(self):
        # Make initial complex get so 'more' will be required
        sinceGetResponse = self.client.get(reverse(views.statements), {"until":self.sixthTime}, X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(sinceGetResponse.status_code, 200)
        rsp = sinceGetResponse.content        
        resp_json = json.loads(rsp)
        resp_url = resp_json['more']
        resp_id = resp_url[-32:]

        self.assertIn(self.guid24, rsp)
        self.assertIn(self.guid23, rsp)
        self.assertIn(self.guid22, rsp)
        self.assertIn(self.guid21, rsp)
        self.assertIn(self.guid20, rsp)
        self.assertIn(self.guid19, rsp)
        self.assertIn(self.guid18, rsp)
        self.assertIn(self.guid17, rsp)
        self.assertIn(self.guid16, rsp)
        self.assertIn(self.guid15, rsp)

        self.assertNotIn(self.guid14, rsp)
        self.assertNotIn(self.guid13, rsp)
        self.assertNotIn(self.guid12, rsp)
        self.assertNotIn(self.guid11, rsp)
        self.assertNotIn(self.guid10, rsp)
        self.assertNotIn(self.guid9, rsp)
        self.assertNotIn(self.guid8, rsp)
        self.assertNotIn(self.guid7, rsp)
        self.assertNotIn(self.guid6, rsp)
        self.assertNotIn(self.guid5, rsp)
        self.assertNotIn(self.guid4, rsp)
        self.assertNotIn(self.guid3, rsp)
        self.assertNotIn(self.guid2, rsp)
        self.assertNotIn(self.guid1, rsp)        
        self.assertNotIn(self.guid25, rsp)

        # Simulate user clicking returned 'more' URL
        moreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}), X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)
        more_rsp = moreURLGet.content
        more_json = json.loads(more_rsp)
        more_resp_url = more_json['more']
        more_resp_id = more_resp_url[-32:]

        self.assertEqual(moreURLGet.status_code, 200)
        self.assertIn(self.guid14, more_rsp)
        self.assertIn(self.guid13, more_rsp)
        self.assertIn(self.guid12, more_rsp)
        self.assertIn(self.guid11, more_rsp)
        self.assertIn(self.guid10, more_rsp)
        self.assertIn(self.guid9, more_rsp)
        self.assertIn(self.guid8, more_rsp)
        self.assertIn(self.guid7, more_rsp)
        self.assertIn(self.guid6, more_rsp)
        self.assertIn(self.guid5, more_rsp)

        self.assertNotIn(self.guid24, more_rsp)
        self.assertNotIn(self.guid23, more_rsp)
        self.assertNotIn(self.guid22, more_rsp)
        self.assertNotIn(self.guid21, more_rsp)
        self.assertNotIn(self.guid20, more_rsp)
        self.assertNotIn(self.guid19, more_rsp)
        self.assertNotIn(self.guid18, more_rsp)
        self.assertNotIn(self.guid17, more_rsp)
        self.assertNotIn(self.guid16, more_rsp)
        self.assertNotIn(self.guid15, more_rsp)
        self.assertNotIn(self.guid4, more_rsp)
        self.assertNotIn(self.guid3, more_rsp)
        self.assertNotIn(self.guid2, more_rsp)
        self.assertNotIn(self.guid1, more_rsp)        
        self.assertNotIn(self.guid25, more_rsp)


        more2URLGet = self.client.get(reverse(views.statements_more, kwargs={'more_id':more_resp_id}), X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(more2URLGet.status_code, 200)
        more2_rsp = more2URLGet.content
        self.assertIn(self.guid4, more2_rsp)
        self.assertIn(self.guid3, more2_rsp)
        self.assertIn(self.guid2, more2_rsp)
        self.assertIn(self.guid1, more2_rsp)

        self.assertNotIn(self.guid25, more2_rsp)
        self.assertNotIn(self.guid24, more2_rsp)
        self.assertNotIn(self.guid23, more2_rsp)
        self.assertNotIn(self.guid22, more2_rsp)
        self.assertNotIn(self.guid21, more2_rsp)
        self.assertNotIn(self.guid20, more2_rsp)
        self.assertNotIn(self.guid19, more2_rsp)
        self.assertNotIn(self.guid18, more2_rsp)
        self.assertNotIn(self.guid17, more2_rsp)
        self.assertNotIn(self.guid16, more2_rsp)
        self.assertNotIn(self.guid15, more2_rsp)
        self.assertNotIn(self.guid14, more2_rsp)
        self.assertNotIn(self.guid13, more2_rsp)
        self.assertNotIn(self.guid12, more2_rsp)
        self.assertNotIn(self.guid11, more2_rsp)        
        self.assertNotIn(self.guid10, more2_rsp)
        self.assertNotIn(self.guid9, more2_rsp)
        self.assertNotIn(self.guid8, more2_rsp)
        self.assertNotIn(self.guid7, more2_rsp)
        self.assertNotIn(self.guid6, more2_rsp)
        self.assertNotIn(self.guid5, more2_rsp)        

        # Simulate user clicking returned 'more' URL
        anotherMoreURLGet = self.client.get(reverse(views.statements_more,kwargs={'more_id':resp_id}), X_Experience_API_Version="0.95",HTTP_AUTHORIZATION=self.auth)
        another_more_rsp = anotherMoreURLGet.content
        another_more_json = json.loads(another_more_rsp)
        another_more_resp_url = another_more_json['more']
        another_more_resp_id = another_more_resp_url[-32:]

        self.assertEqual(anotherMoreURLGet.status_code, 200)
        self.assertIn(self.guid14, another_more_rsp)
        self.assertIn(self.guid13, another_more_rsp)
        self.assertIn(self.guid12, another_more_rsp)
        self.assertIn(self.guid11, another_more_rsp)
        self.assertIn(self.guid10, another_more_rsp)
        self.assertIn(self.guid9, another_more_rsp)
        self.assertIn(self.guid8, another_more_rsp)
        self.assertIn(self.guid7, another_more_rsp)
        self.assertIn(self.guid6, another_more_rsp)
        self.assertIn(self.guid5, another_more_rsp)

        self.assertNotIn(self.guid24, another_more_rsp)
        self.assertNotIn(self.guid23, another_more_rsp)
        self.assertNotIn(self.guid22, another_more_rsp)
        self.assertNotIn(self.guid21, another_more_rsp)
        self.assertNotIn(self.guid20, another_more_rsp)
        self.assertNotIn(self.guid19, another_more_rsp)
        self.assertNotIn(self.guid18, another_more_rsp)
        self.assertNotIn(self.guid17, another_more_rsp)
        self.assertNotIn(self.guid16, another_more_rsp)
        self.assertNotIn(self.guid15, another_more_rsp)
        self.assertNotIn(self.guid4, another_more_rsp)
        self.assertNotIn(self.guid3, another_more_rsp)
        self.assertNotIn(self.guid2, another_more_rsp)
        self.assertNotIn(self.guid1, another_more_rsp)        
        self.assertNotIn(self.guid25, another_more_rsp)

        # Simulate user clicking returned 'more' URL
        anotherMore2URLGet = self.client.get(reverse(views.statements_more, kwargs={'more_id':another_more_resp_id}), X_Experience_API_Version="0.95")
        self.assertEqual(anotherMore2URLGet.status_code, 200)
        another_more2_rsp = anotherMore2URLGet.content
        self.assertIn(self.guid4, another_more2_rsp)
        self.assertIn(self.guid3, another_more2_rsp)
        self.assertIn(self.guid2, another_more2_rsp)
        self.assertIn(self.guid1, another_more2_rsp)

        self.assertNotIn(self.guid25, another_more2_rsp)
        self.assertNotIn(self.guid24, another_more2_rsp)
        self.assertNotIn(self.guid23, another_more2_rsp)
        self.assertNotIn(self.guid22, another_more2_rsp)
        self.assertNotIn(self.guid21, another_more2_rsp)
        self.assertNotIn(self.guid20, another_more2_rsp)
        self.assertNotIn(self.guid19, another_more2_rsp)
        self.assertNotIn(self.guid18, another_more2_rsp)
        self.assertNotIn(self.guid17, another_more2_rsp)
        self.assertNotIn(self.guid16, another_more2_rsp)
        self.assertNotIn(self.guid15, another_more2_rsp)
        self.assertNotIn(self.guid14, another_more2_rsp)
        self.assertNotIn(self.guid13, another_more2_rsp)
        self.assertNotIn(self.guid12, another_more2_rsp)
        self.assertNotIn(self.guid11, another_more2_rsp)        
        self.assertNotIn(self.guid10, another_more2_rsp)
        self.assertNotIn(self.guid9, another_more2_rsp)
        self.assertNotIn(self.guid8, another_more2_rsp)
        self.assertNotIn(self.guid7, another_more2_rsp)
        self.assertNotIn(self.guid6, another_more2_rsp)
        self.assertNotIn(self.guid5, another_more2_rsp)
