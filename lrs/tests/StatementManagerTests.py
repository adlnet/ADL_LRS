import uuid
import json
import urllib
import base64
from django.test import TestCase
from lrs import models, views
from lrs.objects.ActivityManager import ActivityManager
from django.core.urlresolvers import reverse

class StatementManagerTests(TestCase):
    
    @classmethod
    def setUpClass(cls):
        print "\n%s" % __name__

    def setUp(self):
        self.username = "tester1"
        self.email = "test1@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {"username":self.username, "email":self.email,"password":self.password,"password2":self.password}
        self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0.0")

    def test_minimum_stmt(self):
        stmt = json.dumps({"actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)

        activity = models.Activity.objects.get(id=stmt.object_activity.id)
        verb = models.Verb.objects.get(id=stmt.verb.id)
        actor = models.Agent.objects.get(id=stmt.actor.id)

        self.assertEqual(activity.activity_id, "http://example.adlnet.gov/tincan/example/simplestatement")
        self.assertEqual(actor.mbox, "mailto:tincan@adlnet.gov")
        self.assertEqual(verb.verb_id, "http://adlnet.gov/expapi/verbs/created")


    def test_given_stmtID_stmt(self):
        st_id = str(uuid.uuid1())
        stmt = json.dumps({"actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created", "en-GB":"made"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}})
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode({"statementId":st_id}))
        response = self.client.put(path, stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)
        stmt = models.Statement.objects.get(statement_id=st_id)

        activity = models.Activity.objects.get(id=stmt.object_activity.id)
        verb = models.Verb.objects.get(id=stmt.verb.id)
        actor = models.Agent.objects.get(id=stmt.actor.id)
        lang_maps = verb.display

        for k, v in lang_maps.iteritems():
            if k == 'en-GB':
                self.assertEqual(v, 'made')
            elif k == 'en-US':
                self.assertEqual(v, 'created')
        
        self.assertEqual(activity.activity_id, "http://example.adlnet.gov/tincan/example/simplestatement")
        self.assertEqual(actor.mbox, "mailto:tincan@adlnet.gov")
        self.assertEqual(verb.verb_id, "http://adlnet.gov/expapi/verbs/created")
        
        st = models.Statement.objects.get(statement_id=st_id)
        self.assertEqual(st.object_activity.id, activity.id)
        self.assertEqual(st.verb.id, verb.id)

    def test_stmt_ref_as_object(self):
        st_id = str(uuid.uuid1())

        stmt = json.dumps({"actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}})
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode({"statementId":st_id}))
        response = self.client.put(path, stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)

        stmt2 = json.dumps({"actor":{"name":"Example Admin", "mbox":"mailto:admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/attempted"}, 'object': {'objectType':'StatementRef',
            'id': st_id}})
        response = self.client.post(reverse(views.statements), stmt2, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)

        stmts = models.Statement.objects.all()
        stmt_refs = models.StatementRef.objects.filter(ref_id=st_id)
        self.assertEqual(len(stmt_refs), 1)
        self.assertEqual(stmt_refs[0].ref_id, st_id)
        self.assertEqual(len(stmts), 2)

    def test_voided_wrong_type(self):
        stmt = json.dumps({"actor":{"name":"Example Admin", "mbox":"mailto:admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/voided"}, 'object': {'objectType':'Statement', 'id': "12345678-1234-5678-1234-567812345678"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, "The objectType in the statement's object is not valid - Statement")

    def test_no_verb_stmt(self):
        stmt = json.dumps({"actor":{"objectType":"Agent", "mbox":"mailto:t@t.com"}, "object": {'id':'act:activity2'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Statement is missing actor, verb, or object')

    def test_no_object_stmt(self):
        stmt = json.dumps({"actor":{"objectType":"Agent", "mbox":"mailto:t@t.com"}, "verb": {"id":"verb:verb/url"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Statement is missing actor, verb, or object')       

    def test_no_actor_stmt(self):
        stmt = json.dumps({"object":{"id":"act:activity_test"}, "verb": {"id":"verb:verb/url"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Statement is missing actor, verb, or object')

    def test_voided_true_stmt(self):
        stmt = json.dumps({'actor':{'objectType':'Agent', 'mbox':'mailto:l@l.com'}, 'verb': {"id":'verb:verb/url/kicked'},'voided': True, 'object': {'id':'act:activity3'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Invalid field(s) found in Statement - voided')

    def test_result_stmt(self):
        time = "P0Y0M0DT1H311M01S"
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'}, 
            'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity12'},
            "result": {'completion': True, 'success': True, 'response': 'kicked', 'duration': time}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)
        
        activity = models.Activity.objects.get(id=stmt.object_activity.id)

        self.assertEqual(stmt.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.object_activity.id, activity.id)

        st = models.Statement.objects.get(id=stmt.id)
        self.assertEqual(st.object_activity.id, activity.id)

        self.assertEqual(st.result_completion, True)
        self.assertEqual(st.result_success, True)
        self.assertEqual(st.result_response, 'kicked')
        self.assertEqual(st.result_duration, time)

    def test_result_ext_stmt(self):
        time = "P0Y0M0DT1H311M01S"
        stmt = json.dumps({"actor":{'name':'jon',
            'mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity13'}, 
            "result": {'completion': True, 'success': True, 'response': 'yes', 'duration': time,
            'extensions':{'ext:key1': 'value1', 'ext:key2':'value2'}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)
        
        activity = models.Activity.objects.get(id=stmt.object_activity.id)
        actor = models.Agent.objects.get(id=stmt.actor.id)
        extKeys = stmt.result_extensions.keys()
        extVals = stmt.result_extensions.values()

        self.assertEqual(stmt.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.object_activity.id, activity.id)
        self.assertEqual(stmt.actor.id, actor.id)

        st = models.Statement.objects.get(id=stmt.id)
        self.assertEqual(st.object_activity.id, activity.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(st.result_completion, True)
        self.assertEqual(st.result_success, True)
        self.assertEqual(st.result_response, 'yes')
        self.assertEqual(st.result_duration, time)

        self.assertEqual(actor.name, 'jon')
        self.assertEqual(actor.mbox, 'mailto:jon@example.com')
        self.assertEqual(actor.objectType, 'Agent')

        self.assertIn('ext:key1', extKeys)
        self.assertIn('ext:key2', extKeys)
        self.assertIn('value1', extVals)
        self.assertIn('value2', extVals)

    def test_result_score_scaled_up_good(self):
        stmt = json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'scaled':1.0},'completion': True,
            'success': True, 'response': 'yes'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)

    def test_result_score_scaled_down_good(self):
        stmt = json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'scaled':00.000},'completion': True,
            'success': True, 'response': 'yes'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)

    def test_result_score_scaled_up_bad(self):
        stmt = json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'scaled':1.01},'completion': True,
            'success': True, 'response': 'yes'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
                
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Score scaled value in statement result must be between -1 and 1')

    def test_result_score_scaled(self):
        stmt = json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'scaled':-1.00001},'completion': True,
            'success': True, 'response': 'yes'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
                
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Score scaled value in statement result must be between -1 and 1')

    def test_result_score_raw_up_good(self):
        stmt = json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'raw':1.01,'min':-2.0, 'max':1.01},
            'completion': True,'success': True, 'response': 'yes'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)

    def test_result_score_raw_down_good(self):
        stmt = json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'raw':-20.0,'min':-20.0, 'max':1.01},
            'completion': True,'success': True, 'response': 'yes'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)

    def test_result_score_raw_up_bad(self):
        stmt = json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'raw':1.02,'min':-2.0, 'max':1.01},
            'completion': True,'success': True, 'response': 'yes'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
                
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Score raw value in statement result must be between minimum and maximum')

    def test_result_score_raw_down_bad(self):
        stmt = json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'raw':-2.00001,'min':-2.0, 'max':1.01},
            'completion': True,'success': True, 'response': 'yes'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
               
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Score raw value in statement result must be between minimum and maximum')

    def test_result_score_min_max_bad(self):
        stmt = json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'raw':1.5,'min':2.0, 'max':1.01},
            'completion': True,'success': True, 'response': 'yes'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
               
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Score minimum in statement result must be less than the maximum')

    def test_result_score_stmt(self):
        time = "P0Y0M0DT1H311M01S"
        stmt = json.dumps({"actor":{'objectType':'Agent','name':'jon','mbox':'mailto:jon@example.com'},
            'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity14'}, "result": {'score':{'scaled':.95},
            'completion': True, 'success': True, 'response': 'yes', 'duration': time,
            'extensions':{'ext:key1': 'value1', 'ext:key2':'value2'}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)


        activity = models.Activity.objects.get(id=stmt.object_activity.id)
        actor = models.Agent.objects.get(id=stmt.actor.id)
        extKeys = stmt.result_extensions.keys()
        extVals = stmt.result_extensions.values()

        self.assertEqual(stmt.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.object_activity.id, activity.id)
        self.assertEqual(stmt.actor.id, actor.id)

        st = models.Statement.objects.get(id=stmt.id)
        self.assertEqual(st.object_activity.id, activity.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(st.result_completion, True)
        self.assertEqual(st.result_success, True)
        self.assertEqual(st.result_response, 'yes')
        self.assertEqual(st.result_duration, time)

        self.assertEqual(st.result_score_scaled, .95)

        self.assertEqual(activity.activity_id, 'act:activity14')

        self.assertEqual(actor.name, 'jon')
        self.assertEqual(actor.mbox, 'mailto:jon@example.com')

        self.assertIn('ext:key1', extKeys)
        self.assertIn('ext:key2', extKeys)
        self.assertIn('value1', extVals)
        self.assertIn('value2', extVals)


    def test_no_registration_context_stmt(self):
        # expect the LRS to assign a context registration uuid
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},"verb":{"id":"verb:verb/url"},"object": {'id':'act:activity14'},
                         'context': {'contextActivities': {'other': {'id': 'act:NewActivityID'}}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)
        
        self.assertIsNotNone(stmt.context_registration)   

    def test_wrong_statement_type_in_context(self):
        stmt = json.dumps({'actor':{'objectType':'Agent',
            'mbox':'mailto:s@s.com'},'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity16'},
            'context':{'contextActivities': {'other': {'id': 'act:NewActivityID'}},
            'revision': 'foo', 'platform':'bar','language': 'en-US',
            'statement': {'objectType': 'Activity','id': "act:some/act"}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
                
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, "StatementRef objectType must be set to 'StatementRef'")

    def test_invalid_context_registration(self):
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity15'},
                'context':{'registration': "bbb", 'contextActivities': {'other': {'id': 'act:NewActivityID'}, 'grouping':{'id':'act:GroupID'}},
                'revision': 'foo', 'platform':'bar',
                'language': 'en-US'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
                
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Context registration - bbb is not a valid UUID')

    def test_context_stmt(self):
        guid = str(uuid.uuid1())
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity15'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'act:NewActivityID'},
                'grouping':{'id':'act:GroupID'}},'revision': 'foo', 'platform':'bar','language': 'en-US'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)

        activity = models.Activity.objects.get(id=stmt.object_activity.id)
        context_activities = stmt.statementcontextactivity_set.all()

        self.assertEqual(stmt.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.object_activity.id, activity.id)

        st = models.Statement.objects.get(id=stmt.id)
        self.assertEqual(st.object_activity.id, activity.id)
        
        for ca in context_activities:
            if ca.key == 'grouping':
                self.assertEqual(ca.context_activity.all()[0].activity_id, 'act:GroupID')
            elif ca.key == 'other':
                self.assertEqual(ca.context_activity.all()[0].activity_id, 'act:NewActivityID')

        self.assertEqual(st.context_registration, guid)        
        self.assertEqual(st.context_revision, 'foo')
        self.assertEqual(st.context_platform, 'bar')
        self.assertEqual(st.context_language, 'en-US')

    def test_context_activity_list(self):
        guid = str(uuid.uuid1())
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity15'},
                'context':{'registration': guid,
                'contextActivities': {'other': [{'id': 'act:NewActivityID'},{'id':'act:anotherActID'}],
                'grouping':{'id':'act:GroupID'}},
                'revision': 'foo', 'platform':'bar',
                'language': 'en-US'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)

        activity = models.Activity.objects.get(id=stmt.object_activity.id)

        context_activities = models.StatementContextActivity.objects.filter(statement=stmt)
        self.assertEqual(len(context_activities), 2)
        
        context_activity_keys = [ca.key for ca in context_activities]
        self.assertEqual(len(context_activity_keys), 2)
        self.assertIn('grouping', context_activity_keys)
        self.assertIn('other', context_activity_keys)

        context_activity_activities = []        
        for ca in context_activities:
            for c in ca.context_activity.all():
                context_activity_activities.append(c.activity_id)

        self.assertEqual(len(context_activity_activities), 3)

        self.assertIn('act:NewActivityID', context_activity_activities)
        self.assertIn('act:anotherActID', context_activity_activities)
        self.assertIn('act:GroupID', context_activity_activities)

        self.assertEqual(stmt.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.object_activity.id, activity.id)

        st = models.Statement.objects.get(id=stmt.id)
        self.assertEqual(st.object_activity.id, activity.id)

        self.assertEqual(st.context_registration, guid)        
        self.assertEqual(st.context_revision, 'foo')
        self.assertEqual(st.context_platform, 'bar')
        self.assertEqual(st.context_language, 'en-US')

    def test_context_ext_stmt(self):
        guid = str(uuid.uuid1())
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity16'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'act:NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US', 'extensions':{'ext:k1': 'v1', 'ext:k2': 'v2'}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)

        activity = models.Activity.objects.get(id=stmt.object_activity.id)
        extKeys = stmt.context_extensions.keys()
        extVals = stmt.context_extensions.values()
        context_activities = stmt.statementcontextactivity_set.all()

        self.assertEqual(stmt.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.object_activity.id, activity.id)

        st = models.Statement.objects.get(id=stmt.id)
        self.assertEqual(st.object_activity.id, activity.id)

        self.assertEqual(st.context_registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].context_activity.all()[0].activity_id, 'act:NewActivityID')
        self.assertEqual(st.context_revision, 'foo')
        self.assertEqual(st.context_platform, 'bar')
        self.assertEqual(st.context_language, 'en-US')

        self.assertIn('ext:k1', extKeys)
        self.assertIn('ext:k2', extKeys)
        self.assertIn('v1', extVals)
        self.assertIn('v2', extVals)


    def test_stmtref_in_context_stmt(self):
        stmt_guid = str(uuid.uuid1())

        existing_stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
            'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}})
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode({"statementId":stmt_guid}))
        response = self.client.put(path, existing_stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)

        guid = str(uuid.uuid1())
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity16'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'act:NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US',
                'statement': {'objectType': 'StatementRef','id': stmt_guid}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)

        activity = models.Activity.objects.get(id=stmt.object_activity.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.Statement.objects.get(statement_id=stmt_ref.ref_id)

        st = models.Statement.objects.get(id=stmt.id)

        self.assertEqual(st.object_activity.id, activity.id)

        self.assertEqual(st.context_registration, guid)

        self.assertEqual(st.context_revision, 'foo')
        self.assertEqual(st.context_platform, 'bar')
        self.assertEqual(st.context_language, 'en-US')
        self.assertEqual(stmt_ref.ref_id, stmt_guid)
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")

    def test_substmt_in_context_stmt(self):
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity16'},
                'context':{'contextActivities': {'other': {'id': 'act:NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US',
                'statement': {'objectType':'SubStatement', 'actor':{'objectType':'Agent',
                'mbox':'mailto:sss@sss.com'},'verb':{'id':'verb:verb/url/nest/nest'},
                'object':{'id':'act://activity/url'}}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, "StatementRef objectType must be set to 'StatementRef'")

    def test_instructor_in_context_stmt(self):
        stmt_guid = str(uuid.uuid1())
        existing_stmt = json.dumps({'actor':{'objectType':'Agent',
            'mbox':'mailto:s@s.com'},'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}})
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode({"statementId":stmt_guid}))
        response = self.client.put(path, existing_stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)

        guid = str(uuid.uuid1())
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:jon@example.com', 
            'name':'jon'},'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity17'},
            'context':{'registration': guid, 'instructor': {'objectType':'Agent','name':'jon',
            'mbox':'mailto:jon@example.com'},'contextActivities': {'other': {'id': 'act:NewActivityID'}},
            'revision': 'foo', 'platform':'bar','language': 'en-US', 'statement': {'id': stmt_guid,
            'objectType':'StatementRef'}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)

        activity = models.Activity.objects.get(id=stmt.object_activity.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.Statement.objects.get(statement_id=stmt_ref.ref_id)
        context_activities = stmt.statementcontextactivity_set.all()

        st = models.Statement.objects.get(id=stmt.id)

        self.assertEqual(st.object_activity.id, activity.id)

        self.assertEqual(st.context_registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].context_activity.all()[0].activity_id, 'act:NewActivityID')
        self.assertEqual(st.context_revision, 'foo')
        self.assertEqual(st.context_platform, 'bar')
        self.assertEqual(st.context_language, 'en-US')
        
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")
        
        self.assertEqual(st.context_instructor.objectType, 'Agent')
        
        self.assertEqual(st.context_instructor.name, 'jon')
        self.assertEqual(st.context_instructor.mbox, 'mailto:jon@example.com') 


    def test_actor_with_context_stmt(self):
        stmt_guid = str(uuid.uuid1())
        existing_stmt = json.dumps({'actor':{'objectType':'Agent',
            'mbox':'mailto:s@s.com'},'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}})
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode({"statementId":stmt_guid}))
        response = self.client.put(path, existing_stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)

        guid = str(uuid.uuid1())
        stmt = json.dumps({'actor':{'objectType':'Agent', 'name': 'steve',
            'mbox':'mailto:mailto:s@s.com'},'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity18'},
            'context':{'registration': guid, 'instructor': {'objectType':'Agent','name':'jon',
            'mbox':'mailto:jon@example.com'},'contextActivities': {'other': {'id': 'act:NewActivityID1'}},
            'revision': 'foob', 'platform':'bard','language': 'en-US', 'statement': {'id':stmt_guid,
            "objectType":"StatementRef"}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)

        activity = models.Activity.objects.get(id=stmt.object_activity.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.Statement.objects.get(statement_id=stmt_ref.ref_id)
        st = models.Statement.objects.get(id=stmt.id)
        context_activities = stmt.statementcontextactivity_set.all()

        self.assertEqual(st.object_activity.id, activity.id)
        self.assertEqual(st.verb.verb_id, "verb:verb/url" )

        self.assertEqual(st.context_registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].context_activity.all()[0].activity_id, 'act:NewActivityID1')
        self.assertEqual(st.context_revision, 'foob')
        self.assertEqual(st.context_platform, 'bard')
        self.assertEqual(st.context_language, 'en-US')
        
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")
        
        self.assertEqual(st.context_instructor.objectType, 'Agent')
        
        self.assertEqual(st.context_instructor.name, 'jon')
        self.assertEqual(st.context_instructor.mbox, 'mailto:jon@example.com') 


    def test_agent_as_object_with_context_stmt(self):
        stmt_guid = str(uuid.uuid1())
        existing_stmt = json.dumps({'actor':{'objectType':'Agent',
            'mbox':'mailto:mailto:s@s.com'},'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}})
        path = "%s?%s" % (reverse(views.statements), urllib.urlencode({"statementId":stmt_guid}))
        response = self.client.put(path, existing_stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)

        guid = str(uuid.uuid1())
        stmt = json.dumps(
                {'actor':{
                'objectType':'Agent',
                'mbox':'mailto:l@l.com',
                'name':'lou'
                },
                'object':{
                    'objectType':'Agent', 
                    'name': 'lou', 
                    'mbox':'mailto:l@l.com'
                 }, 
                 'verb': {"id":"verb:verb/url"},
                 'context':{
                    'registration': guid, 
                    'instructor': {
                        'objectType':'Agent',
                        'name':'jon',
                        'mbox':'mailto:jon@example.com'
                    },
                    'contextActivities': {
                        'other': {'id': 'act:NewActivityID1'}
                    }, 
                    'language': 'en-US', 
                    'statement': {
                        'id': stmt_guid,
                        'objectType': 'StatementRef'
                    }
                 }
                }
        )
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)

        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.Statement.objects.get(statement_id=stmt_ref.ref_id)
        context_activities = stmt.statementcontextactivity_set.all()

        st = models.Statement.objects.get(id=stmt.id)

        self.assertEqual(st.verb.verb_id, "verb:verb/url")

        self.assertEqual(st.context_registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].context_activity.all()[0].activity_id, 'act:NewActivityID1')
        self.assertEqual(st.context_language, 'en-US')
        
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")
        
        self.assertEqual(st.context_instructor.objectType, 'Agent')
        
        # Should be jon
        self.assertEqual(st.context_instructor.name, 'jon')
        self.assertEqual(st.context_instructor.mbox, 'mailto:jon@example.com') 


    def test_agent_as_object(self):
        stmt = json.dumps({'object':{'objectType':'Agent', 'name': 'lulu', 'openID':'id:luluid'}, 
            'verb': {"id":"verb:verb/url"},'actor':{'objectType':'Agent','mbox':'mailto:t@t.com'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)

        agent = models.Agent.objects.get(id=stmt.object_agent.id)

        self.assertEqual(agent.name, 'lulu')
        self.assertEqual(agent.openID, 'id:luluid')


    def test_unallowed_substmt_field(self):
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
            'verb': {"id":"verb:verb/url"}, 'object':{'objectType':'SubStatement',
            'actor':{'objectType':'Agent','mbox':'mailto:ss@ss.com'},'verb': {"id":"verb:verb/url/nest"},
            'object': {'objectType':'activity', 'id':'act:testex.com'},
            'authority':{'objectType':'Agent','mbox':'mailto:s@s.com'}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Invalid field(s) found in SubStatement - authority')

    def test_nested_substatement(self):
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
            'verb': {"id":"verb:verb/url"}, 'object':{'objectType':'SubStatement',
            'actor':{'objectType':'Agent','mbox':'mailto:ss@ss.com'},'verb': {"id":"verb:verb/url/nest"},
            'object': {'objectType':'SubStatement', 'actor':{'objectType':'Agent','mbox':'mailto:sss@sss.com'},
            'verb':{'id':'verb:verb/url/nest/nest'}, 'object':{'id':'act://activity/url'}}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Cannot nest a SubStatement inside of another SubStatement')        

    def test_substatement_as_object(self):
        guid = str(uuid.uuid1())
        stmt = json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
            'verb': {"id":"verb:verb/url"}, 'object':{'objectType':'SubStatement',
            'actor':{'objectType':'Agent','mbox':'mailto:ss@ss.com'},'verb': {"id":"verb:verb/url/nest"},
            'object': {'objectType':'Activity', 'id':'act:testex.com'}, 'result':{'completion': True, 'success': True,
            'response': 'kicked'}, 'context':{'registration': guid,
            'contextActivities': {'other': {'id': 'act:NewActivityID'}},'revision': 'foo', 'platform':'bar',
            'language': 'en-US', 'extensions':{'ext:k1': 'v1', 'ext:k2': 'v2'}}}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)

        outer_stmt = models.Statement.objects.get(id=stmt.id)
        sub_stmt = models.SubStatement.objects.get(id=outer_stmt.object_substatement.id)
        sub_obj = models.Activity.objects.get(id=sub_stmt.object_activity.id)
        sub_act = models.Agent.objects.get(id=sub_stmt.actor.id)

        self.assertEqual(outer_stmt.verb.verb_id, "verb:verb/url")
        self.assertEqual(outer_stmt.actor.mbox, 'mailto:s@s.com')        
        self.assertEqual(sub_stmt.verb.verb_id, "verb:verb/url/nest")
        self.assertEqual(sub_obj.activity_id, 'act:testex.com')
        self.assertEqual(sub_act.mbox, 'mailto:ss@ss.com')
        self.assertEqual(sub_stmt.context_registration, guid)
        self.assertEqual(sub_stmt.result_response, 'kicked')


    def test_group_stmt(self):
        ot = "Group"
        name = "the group SMT"
        mbox = "mailto:the.groupSMT@example.com"
        members = [{"name":"agentA","mbox":"mailto:agentA@example.com"},
                    {"name":"agentB","mbox":"mailto:agentB@example.com"}]
        testagent = {"objectType":ot, "name":name, "mbox":mbox,"member":members}
        
        stmt = json.dumps({"actor":testagent, 'verb': {"id":"verb:verb/url"},"object": {"id":"act:activity5",
            "objectType": "Activity"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt = models.Statement.objects.get(statement_id=stmt_id)

        activity = models.Activity.objects.get(id=stmt.object_activity.id)
        actor = models.Agent.objects.get(id=stmt.actor.id)

        self.assertEqual(stmt.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.object_activity.id, activity.id)
        self.assertEqual(stmt.actor.id, actor.id)

        st = models.Statement.objects.get(id=stmt.id)
        self.assertEqual(st.object_activity.id, activity.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(actor.name, name)
        self.assertEqual(actor.mbox, mbox)

    def test_activity_correctresponsepattern(self):
        act1 = ActivityManager({
            'objectType': 'Activity', 'id':'act:foo',
            'definition': {'name': {'en-US':'testname'},'description': {'en-US':'testdesc'}, 
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction',
                'interactionType': 'true-false','correctResponsesPattern': ['true'],
                'extensions': {'ext:key1': 'value1'}}})

        act2 = ActivityManager({
            'objectType': 'Activity', 'id':'act:baz',
            'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'}, 
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction',
                'interactionType': 'true-false','correctResponsesPattern': ['true'],
                'extensions': {'ext2:key1': 'value1'}}})


        acts = len(models.Activity.objects.all())
        self.assertEqual(acts, 2)
        self.assertIn('true', act1.Activity.activity_definition_crpanswers)
        self.assertIn('true', act2.Activity.activity_definition_crpanswers)

    # Tests if an act from context already exists in a different stmt, if an act from context is the object in the
    # same stmt, and if an act from context doesn't exist anywhere
    def test_context_statement_delete(self):
        guid = str(uuid.uuid1())
        stmt1 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity'}})
        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt1 = models.Statement.objects.get(statement_id=stmt_id)
        
        st1_id = str(stmt1.statement_id)
        stmt2 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'},
            'context':{'registration': guid, 'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'team':{'objectType': 'Group', 'name':'mygroup',
                    'member':[{"name":"agent_in_group","mbox":"mailto:agentingroup@example.com"}]},
                'contextActivities': {'other': [{'id': 'act:activity'},{'id':'act:activity1'}],
                'grouping':{'id':'act:activity2'}},'revision': 'foo', 'platform':'bar','language': 'en-US',
                'extensions':{'ext:key1': 'value1'},
                'statement':{'objectType': 'StatementRef','id':st1_id}}})
        response = self.client.post(reverse(views.statements), stmt2, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt2 = models.Statement.objects.get(statement_id=stmt_id)

        self.assertEqual(len(models.Statement.objects.all()), 2)
        # Team creates a group object and the agent inside of itself, plus self.auth
        self.assertEqual(len(models.Agent.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Activity.objects.all()), 3)

        models.Statement.objects.get(id=stmt2.id).delete()
        self.assertEqual(len(models.Statement.objects.all()), 1)
        # Agents/activities/verbs are not deleted
        self.assertEqual(len(models.Agent.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Activity.objects.all()), 3)
        self.assertIn('act:activity', models.Activity.objects.values_list('activity_id', flat=True))

    def test_context_in_another_context_statement_delete(self):
        stmt1 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url1"},
            "object": {'id':'act:activity1'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'team':{'objectType': 'Group', 'name':'mygroup',
                    'member':[{"name":"agent_in_group","mbox":"mailto:agentingroup@example.com"}]},
                'contextActivities': {'other': [{'id': 'act:activity1'},{'id':'act:activity2'}],
                'grouping':{'id':'act:activity3'}},'revision': 'foo', 'platform':'bar','language': 'en-US',
                'extensions':{'ext:key1': 'value1'}}})
        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt1 = models.Statement.objects.get(statement_id=stmt_id)

        stmt2 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url2"},
            "object": {'id':'act:activity4'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'team':{'objectType': 'Group', 'name':'mygroup',
                    'member':[{"name":"agent_in_group","mbox":"mailto:agentingroup@example.com"}]},
                'contextActivities': {'other': [{'id': 'act:activity2'},{'id':'act:activity3'}],
                'grouping':{'id':'act:activity5'}},'revision': 'foo', 'platform':'bar','language': 'en-US'}})
        response = self.client.post(reverse(views.statements), stmt2, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt2 = models.Statement.objects.get(statement_id=stmt_id)

        stmt3 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url3"},
            "object": {'id':'act:activity1'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:three@inst.com'},
                'team':{'objectType': 'Group', 'name':'mygroup',
                    'member':[{"name":"agent_in_group","mbox":"mailto:agentingroup@example.com"}]},
                'contextActivities': {'other': [{'id': 'act:activity6'},{'id':'act:activity5'}],
                'grouping':{'id':'act:activity2'}},'revision': 'three', 'platform':'bar','language': 'en-US'}})
        response = self.client.post(reverse(views.statements), stmt3, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt3 = models.Statement.objects.get(statement_id=stmt_id)

        self.assertEqual(len(models.Activity.objects.all()), 6)
        self.assertEqual(len(models.Agent.objects.all()), 8)
        self.assertEqual(len(models.Verb.objects.all()), 3)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 6)
        self.assertEqual(len(models.Statement.objects.all()), 3)

        models.Statement.objects.get(id=stmt3.id).delete()
        # Agents/activities/verbs are not deleted
        self.assertEqual(len(models.Activity.objects.all()), 6)
        self.assertEqual(len(models.Agent.objects.all()), 8)        
        self.assertEqual(len(models.Verb.objects.all()), 3)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 4)
        self.assertEqual(len(models.Statement.objects.all()), 2)

        models.Statement.objects.get(id=stmt2.id).delete()
        self.assertEqual(len(models.Activity.objects.all()), 6)
        self.assertEqual(len(models.Agent.objects.all()), 8)        
        self.assertEqual(len(models.Verb.objects.all()), 3)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 2)
        self.assertEqual(len(models.Statement.objects.all()), 1)

        models.Statement.objects.get(id=stmt1.id).delete()
        self.assertEqual(len(models.Activity.objects.all()), 6)
        self.assertEqual(len(models.Agent.objects.all()), 8)        
        self.assertEqual(len(models.Verb.objects.all()), 3)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 0)
        self.assertEqual(len(models.Statement.objects.all()), 0)

    def test_simple_statement_delete(self):
        stmt1 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'}})
        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt1 = models.Statement.objects.get(statement_id=stmt_id)

        stmt2 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:b@b.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'}})
        response = self.client.post(reverse(views.statements), stmt2, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt2 = models.Statement.objects.get(statement_id=stmt_id)

        self.assertEqual(len(models.Agent.objects.all()), 3)
        self.assertEqual(len(models.Activity.objects.all()), 1)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Statement.objects.all()), 2)

        models.Statement.objects.get(id=stmt2.id).delete()

        self.assertEqual(len(models.Agent.objects.all()), 3)
        self.assertEqual(len(models.Activity.objects.all()), 1)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Statement.objects.all()), 1)
        self.assertEqual(models.Statement.objects.all()[0].id, stmt1.id)

    def test_more_conacts_delete(self):
        stmt1 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'}})
        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt1 = models.Statement.objects.get(statement_id=stmt_id)

        stmt2 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity2'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'contextActivities': {'other': {'id': 'act:activity1'}},'revision': 'foo', 'platform':'bar',
                'language': 'en-US'}})
        response = self.client.post(reverse(views.statements), stmt2, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt2 = models.Statement.objects.get(statement_id=stmt_id)

        self.assertEqual(len(models.Agent.objects.all()), 3)
        self.assertEqual(len(models.Activity.objects.all()), 2)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Statement.objects.all()), 2)

        models.Statement.objects.get(id=stmt2.id).delete()

        self.assertEqual(len(models.Agent.objects.all()), 3)
        self.assertEqual(len(models.Activity.objects.all()), 2)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Statement.objects.all()), 1)

    def test_activity_also_in_conact(self):
        stmt1 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'contextActivities': {'other': {'id': 'act:activity2'}},'revision': 'foo', 'platform':'bar',
                'language': 'en-US'}})
        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt1 = models.Statement.objects.get(statement_id=stmt_id)

        stmt2 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity2'}})
        response = self.client.post(reverse(views.statements), stmt2, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt2 = models.Statement.objects.get(statement_id=stmt_id)

        self.assertEqual(len(models.Agent.objects.all()), 3)
        self.assertEqual(len(models.Activity.objects.all()), 2)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Statement.objects.all()), 2)

        models.Statement.objects.get(id=stmt2.id).delete()

        self.assertEqual(len(models.Agent.objects.all()), 3)
        self.assertEqual(len(models.Activity.objects.all()), 2)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Statement.objects.all()), 1)


        agents = models.Agent.objects.values_list('mbox', flat=True)
        self.assertIn('mailto:a@a.com', agents)
        self.assertIn('mailto:inst@inst.com', agents)
        
        acts = models.Activity.objects.values_list('activity_id', flat=True)
        self.assertIn('act:activity1', acts)
        self.assertIn('act:activity2', acts)
        self.assertEqual(models.Verb.objects.all()[0].verb_id, 'verb:verb/url')
        self.assertEqual(models.Statement.objects.all()[0].id, stmt1.id)

    def test_sub_delete(self):
        stmt1 = json.dumps(
            {"actor":{"objectType":"Agent","mbox":"mailto:out@out.com"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/1"},
            "object":{"objectType":"SubStatement",
                "actor":{"objectType":"Agent","mbox":"mailto:sub@sub.com"},
                "verb": {"id":"verb:verb/url/nest1"},
                "object": {"objectType":"Activity", "id":"act:subactivity1"},
                "result":{"completion": True, "success": True,"response": "kicked"},
                "context":{"contextActivities": {"other": {"id": "act:subconactivity1"}},
                    'team':{'objectType': 'Group', 'name':'conteamgroup',
                    'member':[{"name":"agent_in_conteamgroup","mbox":"mailto:actg@actg.com"}]},"revision": "foo",
                    "platform":"bar","language": "en-US","extensions":{"ext:k1": "v1", "ext:k2": "v2"}}}})
        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt1 = models.Statement.objects.get(statement_id=stmt_id)

        stmt2 = json.dumps(
            {"actor": {"objectType": "Agent", "mbox": "mailto:ref@ref.com"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/2"},
            "object":{"objectType": "StatementRef", "id":str(stmt1.statement_id)}})
        response = self.client.post(reverse(views.statements), stmt2, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt2 = models.Statement.objects.get(statement_id=stmt_id)

        stmt3 = json.dumps(
            {"actor": {"objectType": "Agent", "mbox": "mailto:norm@norm.com"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/3"},
            "object":{"objectType": "Activity", "id":"act:activity1"}})
        response = self.client.post(reverse(views.statements), stmt3, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt3 = models.Statement.objects.get(statement_id=stmt_id)

        stmt4 = json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/4"},
            "object": {'id':'act:activity2'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'contextActivities': {'other': {'id': 'act:conactivity1'}},'revision': 'foo', 'platform':'bar',
                'language': 'en-US', 'statement':{'objectType': 'StatementRef',
                'id':str(stmt3.statement_id)}}})
        response = self.client.post(reverse(views.statements), stmt4, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        stmt_id = json.loads(response.content)[0]
        stmt4 = models.Statement.objects.get(statement_id=stmt_id)

        self.assertEqual(len(models.Statement.objects.all()), 4)
        self.assertEqual(len(models.Agent.objects.all()), 9)
        self.assertEqual(len(models.Activity.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 5)
        self.assertEqual(len(models.SubStatement.objects.all()), 1)
        self.assertEqual(len(models.StatementRef.objects.all()), 1)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 1)
        self.assertEqual(len(models.SubStatementContextActivity.objects.all()), 1)
        models.Statement.objects.get(id=stmt4.id).delete()

        self.assertEqual(len(models.Statement.objects.all()), 3)
        self.assertEqual(len(models.Agent.objects.all()), 9)
        self.assertEqual(len(models.Activity.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 5)
        self.assertEqual(len(models.SubStatement.objects.all()), 1)
        self.assertEqual(len(models.StatementRef.objects.all()), 1)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 0)
        self.assertEqual(len(models.SubStatementContextActivity.objects.all()), 1)
        models.Statement.objects.get(id=stmt3.id).delete()

        self.assertEqual(len(models.Statement.objects.all()), 2)
        self.assertEqual(len(models.Agent.objects.all()), 9)
        self.assertEqual(len(models.Activity.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 5)
        self.assertEqual(len(models.SubStatement.objects.all()), 1)
        self.assertEqual(len(models.StatementRef.objects.all()), 1)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 0)
        self.assertEqual(len(models.SubStatementContextActivity.objects.all()), 1)
        models.Statement.objects.get(id=stmt2.id).delete()

        self.assertEqual(len(models.Statement.objects.all()), 1)
        self.assertEqual(len(models.Agent.objects.all()), 9)
        self.assertEqual(len(models.Activity.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 5)
        self.assertEqual(len(models.SubStatement.objects.all()), 1)
        self.assertEqual(len(models.StatementRef.objects.all()), 0)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 0)
        self.assertEqual(len(models.SubStatementContextActivity.objects.all()), 1)
        models.Statement.objects.get(id=stmt1.id).delete()

        self.assertEqual(len(models.Statement.objects.all()), 0)
        self.assertEqual(len(models.Agent.objects.all()), 9)
        self.assertEqual(len(models.Activity.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 5)
        self.assertEqual(len(models.SubStatement.objects.all()), 0)
        self.assertEqual(len(models.StatementRef.objects.all()), 0)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 0)
        self.assertEqual(len(models.SubStatementContextActivity.objects.all()), 0)
