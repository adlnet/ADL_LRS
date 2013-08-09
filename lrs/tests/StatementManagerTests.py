import uuid
import json
from datetime import datetime
from django.test import TestCase
from lrs import models, views
from lrs.exceptions import ParamError, Forbidden, ParamConflict, IDNotFoundError
from lrs.objects.ActivityManager import ActivityManager
from lrs.objects.StatementManager import StatementManager
from django.core.urlresolvers import reverse
from django.conf import settings
import base64

class StatementManagerTests(TestCase):
    
    def setUp(self):
        if not settings.HTTP_AUTH_ENABLED:
            settings.HTTP_AUTH_ENABLED = True
        
        self.username = "tester1"
        self.email = "test1@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {"username":self.username, "email":self.email,"password":self.password,"password2":self.password}
        response = self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0.0")

        if settings.HTTP_AUTH_ENABLED:
            response = self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0.0")

    def test_minimum_stmt(self):
        stmt = StatementManager(json.dumps({"actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))

        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)
        verb = models.Verb.objects.get(id=stmt.model_object.verb.id)
        actor = models.Agent.objects.get(id=stmt.model_object.actor.id)

        self.assertEqual(activity.activity_id, "http://example.adlnet.gov/tincan/example/simplestatement")
        self.assertEqual(actor.mbox, "mailto:tincan@adlnet.gov")
        self.assertEqual(verb.verb_id, "http://adlnet.gov/expapi/verbs/created")


    def test_given_stmtID_stmt(self):
        st_id = str(uuid.uuid1())
        stmt = StatementManager(json.dumps({"id":st_id,
            "actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created", "en-GB":"made"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))
        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)
        verb = models.Verb.objects.get(id=stmt.model_object.verb.id)
        actor = models.Agent.objects.get(id=stmt.model_object.actor.id)
        lang_maps = json.loads(verb.display)

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


    def test_existing_stmtID_stmt(self):
        st_id = str(uuid.uuid1())
        stmt = StatementManager(json.dumps({"id":st_id,"verb":{"id":"verb:verb/url",
            "display":{"en-US":"myverb"}}, "object": {"id":"act:activity"}, "actor":{"objectType":"Agent",
            "mbox":"mailto:t@t.com"}}))
        self.assertRaises(ParamConflict, StatementManager, json.dumps({"id":st_id,
            "verb":{"id":"verb:verb/url","display":{"en-US":"myverb"}},"object": {'id':'act:activity2'},
            "actor":{"objectType":"Agent", "mbox":"mailto:t@t.com"}}))

    def test_voided_stmt(self):
        stmt = StatementManager(json.dumps({"actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))

        st_id = stmt.model_object.statement_id
        st_model = models.Statement.objects.get(statement_id=st_id)
        self.assertEqual(st_model.voided, False)

        stmt2 = StatementManager(json.dumps({"actor":{"name":"Example Admin", "mbox":"mailto:admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/voided"}, 'object': {'objectType':'StatementRef',
            'id': str(st_id)}}))
        
        st_model = models.Statement.objects.get(statement_id=st_id)        
        self.assertEqual(st_model.voided, True)

        stmt_ref = models.StatementRef.objects.get(ref_id=str(st_id))
        self.assertEqual(stmt_ref.object_type, 'StatementRef')


    def test_stmt_ref_as_object(self):
        st_id = str(uuid.uuid1())

        stmt = StatementManager(json.dumps({"actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"},
            "id":st_id}))

        stmt2 = StatementManager(json.dumps({"actor":{"name":"Example Admin", "mbox":"mailto:admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/attempted"}, 'object': {'objectType':'StatementRef',
            'id': st_id}}))

        stmts = models.Statement.objects.all()
        stmt_refs = models.StatementRef.objects.filter(ref_id=st_id)
        self.assertEqual(len(stmt_refs), 1)
        self.assertEqual(stmt_refs[0].ref_id, st_id)
        self.assertEqual(len(stmts), 2)

    def test_stmt_ref_no_existing_stmt(self):
        self.assertRaises(IDNotFoundError, StatementManager, json.dumps({"actor":{"name":"Example Admin", "mbox":"mailto:admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/attempted"}, 'object': {'objectType':'StatementRef',
            'id': "12345678-1234-5678-1234-567812345678"}}))

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
        self.assertEqual(response.content, 'verb is missing in Statement')

    def test_no_object_stmt(self):
        stmt = json.dumps({"actor":{"objectType":"Agent", "mbox":"mailto:t@t.com"}, "verb": {"id":"verb:verb/url"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'object is missing in Statement')       

    def test_no_actor_stmt(self):
        stmt = json.dumps({"object":{"id":"act:activity_test"}, "verb": {"id":"verb:verb/url"}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'actor is missing in Statement')

    def test_voided_true_stmt(self):
        stmt = json.dumps({'actor':{'objectType':'Agent', 'mbox':'mailto:l@l.com'}, 'verb': {"id":'verb:verb/url/kicked'},'voided': True, 'object': {'id':'act:activity3'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Invalid field(s) found in Statement - voided')

    def test_result_stmt(self):
        time = "P0Y0M0DT1H311M01S"
        stmt = StatementManager(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'}, 
            'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity12'},
            "result": {'completion': True, 'success': True, 'response': 'kicked', 'duration': time}}))
        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.object_activity.id, activity.id)

        st = models.Statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.object_activity.id, activity.id)

        self.assertEqual(st.result_completion, True)
        self.assertEqual(st.result_success, True)
        self.assertEqual(st.result_response, 'kicked')
        self.assertEqual(st.result_duration, time)

    def test_result_ext_stmt(self):
        time = "P0Y0M0DT1H311M01S"
        stmt = StatementManager(json.dumps({"actor":{'name':'jon',
            'mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity13'}, 
            "result": {'completion': True, 'success': True, 'response': 'yes', 'duration': time,
            'extensions':{'ext:key1': 'value1', 'ext:key2':'value2'}}}))
        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)
        actor = models.Agent.objects.get(id=stmt.model_object.actor.id)
        extKeys = stmt.model_object.result_extensions.keys()
        extVals = stmt.model_object.result_extensions.values()

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.object_activity.id, activity.id)
        self.assertEqual(stmt.model_object.actor.id, actor.id)

        st = models.Statement.objects.get(id=stmt.model_object.id)
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
        stmt = StatementManager(json.dumps({"actor":{'objectType':'Agent','name':'jon','mbox':'mailto:jon@example.com'},
            'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity14'}, "result": {'score':{'scaled':.95},
            'completion': True, 'success': True, 'response': 'yes', 'duration': time,
            'extensions':{'ext:key1': 'value1', 'ext:key2':'value2'}}}))

        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)
        actor = models.Agent.objects.get(id=stmt.model_object.actor.id)
        extKeys = stmt.model_object.result_extensions.keys()
        extVals = stmt.model_object.result_extensions.values()

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.object_activity.id, activity.id)
        self.assertEqual(stmt.model_object.actor.id, actor.id)

        st = models.Statement.objects.get(id=stmt.model_object.id)
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
        stmt = StatementManager(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},"verb":{"id":"verb:verb/url"},"object": {'id':'act:activity14'},
                         'context': {'contextActivities': {'other': {'id': 'act:NewActivityID'}}}})).model_object
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
        stmt = StatementManager(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity15'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'act:NewActivityID'},
                'grouping':{'id':'act:GroupID'}},'revision': 'foo', 'platform':'bar','language': 'en-US'}}))

        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)
        context_activities = stmt.model_object.statementcontextactivity_set.all()

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.object_activity.id, activity.id)

        st = models.Statement.objects.get(id=stmt.model_object.id)
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
        stmt = StatementManager(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity15'},
                'context':{'registration': guid,
                'contextActivities': {'other': [{'id': 'act:NewActivityID'},{'id':'act:anotherActID'}],
                'grouping':{'id':'act:GroupID'}},
                'revision': 'foo', 'platform':'bar',
                'language': 'en-US'}}))
        
        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)

        context_activities = models.StatementContextActivity.objects.filter(statement=stmt.model_object)
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

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.object_activity.id, activity.id)

        st = models.Statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.object_activity.id, activity.id)

        self.assertEqual(st.context_registration, guid)        
        self.assertEqual(st.context_revision, 'foo')
        self.assertEqual(st.context_platform, 'bar')
        self.assertEqual(st.context_language, 'en-US')

    def test_context_ext_stmt(self):
        guid = str(uuid.uuid1())
        stmt = StatementManager(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity16'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'act:NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US', 'extensions':{'ext:k1': 'v1', 'ext:k2': 'v2'}}}))

        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)
        extKeys = stmt.model_object.context_extensions.keys()
        extVals = stmt.model_object.context_extensions.values()
        context_activities = stmt.model_object.statementcontextactivity_set.all()

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.object_activity.id, activity.id)

        st = models.Statement.objects.get(id=stmt.model_object.id)
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

        existing_stmt = StatementManager(json.dumps({'id':stmt_guid, 'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
            'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}}))

        guid = str(uuid.uuid1())
        stmt = StatementManager(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity16'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'act:NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US',
                'statement': {'objectType': 'StatementRef','id': stmt_guid}}}))

        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.Statement.objects.get(statement_id=stmt_ref.ref_id)

        st = models.Statement.objects.get(id=stmt.model_object.id)

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
        existing_stmt = StatementManager(json.dumps({'id':stmt_guid, 'actor':{'objectType':'Agent',
            'mbox':'mailto:s@s.com'},'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}}))

        guid = str(uuid.uuid1())
        stmt = StatementManager(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:jon@example.com', 
            'name':'jon'},'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity17'},
            'context':{'registration': guid, 'instructor': {'objectType':'Agent','name':'jon',
            'mbox':'mailto:jon@example.com'},'contextActivities': {'other': {'id': 'act:NewActivityID'}},
            'revision': 'foo', 'platform':'bar','language': 'en-US', 'statement': {'id': stmt_guid,
            'objectType':'StatementRef'}}}))

        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.Statement.objects.get(statement_id=stmt_ref.ref_id)
        context_activities = stmt.model_object.statementcontextactivity_set.all()

        st = models.Statement.objects.get(id=stmt.model_object.id)

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
        existing_stmt = StatementManager(json.dumps({'id':stmt_guid, 'actor':{'objectType':'Agent',
            'mbox':'mailto:s@s.com'},'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}}))

        guid = str(uuid.uuid1())
        stmt = StatementManager(json.dumps({'actor':{'objectType':'Agent', 'name': 'steve',
            'mbox':'mailto:mailto:s@s.com'},'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity18'},
            'context':{'registration': guid, 'instructor': {'objectType':'Agent','name':'jon',
            'mbox':'mailto:jon@example.com'},'contextActivities': {'other': {'id': 'act:NewActivityID1'}},
            'revision': 'foob', 'platform':'bard','language': 'en-US', 'statement': {'id':stmt_guid,
            "objectType":"StatementRef"}}}))

        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.Statement.objects.get(statement_id=stmt_ref.ref_id)
        st = models.Statement.objects.get(id=stmt.model_object.id)
        context_activities = stmt.model_object.statementcontextactivity_set.all()

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
        existing_stmt = StatementManager(json.dumps({'id':stmt_guid, 'actor':{'objectType':'Agent',
            'mbox':'mailto:mailto:s@s.com'},'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}}))

        guid = str(uuid.uuid1())
        stmt = StatementManager(
            json.dumps(
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
                    'revision': 'foob', 
                    'platform':'bard',
                    'language': 'en-US', 
                    'statement': {
                        'id': stmt_guid,
                        'objectType': 'StatementRef'
                    }
                 }
                }
            )
        )

        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.Statement.objects.get(statement_id=stmt_ref.ref_id)
        context_activities = stmt.model_object.statementcontextactivity_set.all()

        st = models.Statement.objects.get(id=stmt.model_object.id)

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
        guid = str(uuid.uuid1())
        stmt = StatementManager(json.dumps({'object':{'objectType':'Agent', 'name': 'lulu', 'openID':'id:luluid'}, 
            'verb': {"id":"verb:verb/url"},'actor':{'objectType':'Agent','mbox':'mailto:t@t.com'}}))

        st = models.Statement.objects.get(id=stmt.model_object.id)
        agent = models.Agent.objects.get(id=stmt.model_object.object_agent.id)

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
        stmt = StatementManager(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
            'verb': {"id":"verb:verb/url"}, 'object':{'objectType':'SubStatement',
            'actor':{'objectType':'Agent','mbox':'mailto:ss@ss.com'},'verb': {"id":"verb:verb/url/nest"},
            'object': {'objectType':'Activity', 'id':'act:testex.com'}, 'result':{'completion': True, 'success': True,
            'response': 'kicked'}, 'context':{'registration': guid,
            'contextActivities': {'other': {'id': 'act:NewActivityID'}},'revision': 'foo', 'platform':'bar',
            'language': 'en-US', 'extensions':{'ext:k1': 'v1', 'ext:k2': 'v2'}}}}))

        outer_stmt = models.Statement.objects.get(id=stmt.model_object.id)
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
        testagent = json.dumps({"objectType":ot, "name":name, "mbox":mbox,"member":members})
        
        stmt = StatementManager(json.dumps({"actor":testagent, 'verb': {"id":"verb:verb/url"},"object": {"id":"act:activity5",
            "objectType": "Activity"}}))
        activity = models.Activity.objects.get(id=stmt.model_object.object_activity.id)
        actor = models.Agent.objects.get(id=stmt.model_object.actor.id)

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.object_activity.id, activity.id)
        self.assertEqual(stmt.model_object.actor.id, actor.id)

        st = models.Statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.object_activity.id, activity.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(actor.name, name)
        self.assertEqual(actor.mbox, mbox)

    def test_activity_definition_delete(self):
        act1 = ActivityManager(json.dumps({'objectType': 'Activity', 'id':'act:foo',
                'definition': {'name': {'en-UK':'name', 'en-US':'nombre'},'description': {'en-UK':'desc',
                'en-US': 'tdesc'},'type': 'type:course','interactionType': 'intType2',
                'extensions': {'ext:key1': 'value1','ext:key2': 'value2','ext:key3': 'value3'}}}))

        act2 = ActivityManager(json.dumps({'objectType': 'Activity', 'id':'act:baz',
                'definition': {'name': {'en-UK':'name2', 'en-US':'nombre2'},'description': {'en-UK':'desc2',
                'en-US': 'tdesc2'},'type': 'type:course','interactionType': 'intType2',
                'extensions': {'ext2:key1': 'value1','ext2:key2': 'value2','ext2:key3': 'value3'}}}))

        
        name_lang1_1 = models.ActivityDefinitionNameLangMap.objects.get(value='name')
        name_lang1_2 = models.ActivityDefinitionNameLangMap.objects.get(value='nombre')
        name_lang2_1= models.ActivityDefinitionNameLangMap.objects.get(value='name2')
        name_lang2_2= models.ActivityDefinitionNameLangMap.objects.get(value='nombre2')
        
        desc_lang1_1 = models.ActivityDefinitionDescLangMap.objects.get(value='desc')
        desc_lang1_2 = models.ActivityDefinitionDescLangMap.objects.get(value='tdesc')
        desc_lang2_1 = models.ActivityDefinitionDescLangMap.objects.get(value='desc2')
        desc_lang2_2 = models.ActivityDefinitionDescLangMap.objects.get(value='tdesc2')
        
        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        self.assertEqual(name_langs, 4)
        self.assertEqual(desc_langs, 4)
        self.assertEqual(acts, 2)
        
        # Should only be three name_langs now
        models.ActivityDefinitionNameLangMap.objects.get(id=name_lang1_1.id).delete()
        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        self.assertEqual(name_langs, 3)
        self.assertEqual(desc_langs, 4)
        self.assertEqual(acts, 2)

        # Should only be three desc_langs now
        models.ActivityDefinitionDescLangMap.objects.get(id=desc_lang2_1.id).delete()
        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        self.assertEqual(name_langs, 3)
        self.assertEqual(desc_langs, 3)
        self.assertEqual(acts, 2)

        # Activity 2 will still remain
        models.Activity.objects.get(id=act1.Activity.id).delete()
        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        self.assertEqual(name_langs, 2)
        self.assertEqual(desc_langs, 1)
        self.assertEqual(acts, 1)

    def test_activity_correctresponsepattern(self):
        act1 = ActivityManager(json.dumps({
            'objectType': 'Activity', 'id':'act:foo',
            'definition': {'name': {'en-US':'testname'},'description': {'en-US':'testdesc'}, 
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction',
                'interactionType': 'true-false','correctResponsesPattern': ['true'],
                'extensions': {'ext:key1': 'value1'}}}))

        act2 = ActivityManager(json.dumps({
            'objectType': 'Activity', 'id':'act:baz',
            'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'}, 
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction',
                'interactionType': 'true-false','correctResponsesPattern': ['true'],
                'extensions': {'ext2:key1': 'value1'}}}))

        
        name_lang1 = models.ActivityDefinitionNameLangMap.objects.get(value='testname')
        name_lang2 = models.ActivityDefinitionNameLangMap.objects.get(value='testname2')
        
        desc_lang1 = models.ActivityDefinitionDescLangMap.objects.get(value='testdesc')
        desc_lang2 = models.ActivityDefinitionDescLangMap.objects.get(value='testdesc2')
        
        crp_answer1 = models.CorrectResponsesPatternAnswer.objects.get(activity=act1.Activity)
        crp_answer2 = models.CorrectResponsesPatternAnswer.objects.get(activity=act2.Activity)        

        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        crp_answers = len(models.CorrectResponsesPatternAnswer.objects.all())
        self.assertEqual(name_langs, 2)
        self.assertEqual(desc_langs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crp_answers, 2)

        # Should only be 1 name_langs now
        models.ActivityDefinitionNameLangMap.objects.get(id=name_lang1.id).delete()
        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        crp_answers = len(models.CorrectResponsesPatternAnswer.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crp_answers, 2)

        # Should only be 1 desc_langs now
        models.ActivityDefinitionDescLangMap.objects.get(id=desc_lang2.id).delete()
        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        crp_answers = len(models.CorrectResponsesPatternAnswer.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 1)
        self.assertEqual(acts, 2)
        self.assertEqual(crp_answers, 2)

        # Deletes its desc lang, def, crp, and crp answer
        models.Activity.objects.get(id=act1.Activity.id).delete()
        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        crp_answers = len(models.CorrectResponsesPatternAnswer.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 0)
        self.assertEqual(acts, 1)
        self.assertEqual(crp_answers, 1)

    # Would be same for steps, target/source, and scale
    def test_activity_definition_choices(self):
        act1 = ActivityManager(json.dumps(
            {'objectType': 'Activity', 'id':'act:foo',
                'definition': {'name': {'en-US':'testname1'},'description': {'en-US':'testdesc1'},
                    'type': 'http://adlnet.gov/expapi/activities/cmi.interaction',
                    'interactionType': 'choice',
                    'correctResponsesPattern': ['golf', 'tetris'],'choices':[
                    {'id': 'golf', 'description': {'en-US':'Golf Example', 'en-GB': 'GOLF'}},
                    {'id': 'tetris','description':{'en-US': 'Tetris Example', 'en-GB': 'TETRIS'}},
                    {'id':'facebook', 'description':{'en-US':'Facebook App', 'en-GB': 'FACEBOOK'}},
                    {'id':'scrabble', 'description': {'en-US': 'Scrabble Example', 'en-GB': 'SCRABBLE'}}],
                    'extensions': {'ext1:key1': 'value1'}}}))

        act2 = ActivityManager(json.dumps(
            {'objectType': 'Activity', 'id':'act:biz',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'},
                    'type': 'http://adlnet.gov/expapi/activities/cmi.interaction',
                    'interactionType': 'choice',
                    'correctResponsesPattern': ['golf', 'tetris'],'choices':[
                    {'id': 'golf', 'description': {'en-US':'Golf Example', 'en-GB': 'GOLF'}},
                    {'id': 'tetris','description':{'en-US': 'Tetris Example', 'en-GB': 'TETRIS'}},
                    {'id':'facebook', 'description':{'en-US':'Facebook App', 'en-GB': 'FACEBOOK'}},
                    {'id':'scrabble', 'description': {'en-US': 'Scrabble Example', 'en-GB': 'SCRABBLE'}}],
                    'extensions': {'ext2:key1': 'value1'}}}))
        
        name_lang1 = models.ActivityDefinitionNameLangMap.objects.get(value='testname1')
        name_lang2 = models.ActivityDefinitionNameLangMap.objects.get(value='testname2')
        
        desc_lang1 = models.ActivityDefinitionDescLangMap.objects.get(value='testdesc1')
        desc_lang2 = models.ActivityDefinitionDescLangMap.objects.get(value='testdesc2')
        
        crp_answers1 = models.CorrectResponsesPatternAnswer.objects.filter(activity=act1.Activity)
        crp_answers2 = models.CorrectResponsesPatternAnswer.objects.filter(activity=act2.Activity)        

        choices1 = models.ActivityDefinitionChoice.objects.filter(activity=act1.Activity)
        choices2 = models.ActivityDefinitionChoice.objects.filter(activity=act2.Activity)

        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        crp_answers = len(models.CorrectResponsesPatternAnswer.objects.all())
        choices = len(models.ActivityDefinitionChoice.objects.all())
        choice_lang_maps = len(models.ActivityDefinitionChoiceDesc.objects.all())
        self.assertEqual(name_langs, 2)
        self.assertEqual(desc_langs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crp_answers, 4)
        self.assertEqual(choices, 8)
        self.assertEqual(choice_lang_maps, 16)

        # Should only be 1 name_langs now
        models.ActivityDefinitionNameLangMap.objects.get(id=name_lang1.id).delete()
        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        crp_answers = len(models.CorrectResponsesPatternAnswer.objects.all())
        choices = len(models.ActivityDefinitionChoice.objects.all())
        choice_lang_maps = len(models.ActivityDefinitionChoiceDesc.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crp_answers, 4)
        self.assertEqual(choices, 8)
        self.assertEqual(choice_lang_maps, 16)

        # Should only be 1 desc_langs now
        models.ActivityDefinitionDescLangMap.objects.get(id=desc_lang2.id).delete()
        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        crp_answers = len(models.CorrectResponsesPatternAnswer.objects.all())
        choices = len(models.ActivityDefinitionChoice.objects.all())
        choice_lang_maps = len(models.ActivityDefinitionChoiceDesc.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 1)
        self.assertEqual(acts, 2)
        self.assertEqual(crp_answers, 4)
        self.assertEqual(choices, 8)
        self.assertEqual(choice_lang_maps, 16)

        # Delete activity - removes its desc lang, def, crp, crp answers and choices
        models.Activity.objects.get(id=act1.Activity.id).delete()
        name_langs = len(models.ActivityDefinitionNameLangMap.objects.all())
        desc_langs = len(models.ActivityDefinitionDescLangMap.objects.all())
        acts = len(models.Activity.objects.all())
        crp_answers = len(models.CorrectResponsesPatternAnswer.objects.all())
        choices = len(models.ActivityDefinitionChoice.objects.all())
        choice_lang_maps = len(models.ActivityDefinitionChoiceDesc.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 0)
        self.assertEqual(acts, 1)
        self.assertEqual(crp_answers, 2)
        self.assertEqual(choices, 4)
        self.assertEqual(choice_lang_maps, 8)

    # Tests if an act from context already exists in a different stmt, if an act from context is the object in the
    # same stmt, and if an act from context doesn't exist anywhere
    def test_context_statement_delete(self):
        guid = str(uuid.uuid1())
        stmt1 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity'}}))
        
        st1_id = str(stmt1.model_object.statement_id)
        stmt2 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'},
            'context':{'registration': guid, 'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'team':{'objectType': 'Group', 'name':'mygroup',
                    'member':[{"name":"agent_in_group","mbox":"mailto:agentingroup@example.com"}]},
                'contextActivities': {'other': [{'id': 'act:activity'},{'id':'act:activity1'}],
                'grouping':{'id':'act:activity2'}},'revision': 'foo', 'platform':'bar','language': 'en-US',
                'extensions':{'ext:key1': 'value1'},
                'statement':{'objectType': 'StatementRef','id':st1_id}}}))

        self.assertEqual(len(models.Statement.objects.all()), 2)
        # Team creates a group object and the agent inside of itself
        self.assertEqual(len(models.Agent.objects.all()), 4)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Activity.objects.all()), 3)

        models.Statement.objects.get(id=stmt2.model_object.id).delete()
        self.assertEqual(len(models.Statement.objects.all()), 1)
        # Agents/activities/verbs are not deleted
        self.assertEqual(len(models.Agent.objects.all()), 4)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Activity.objects.all()), 3)
        self.assertIn('act:activity', models.Activity.objects.values_list('activity_id', flat=True))

    def test_context_in_another_context_statement_delete(self):
        stmt1 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url1"},
            "object": {'id':'act:activity1'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'team':{'objectType': 'Group', 'name':'mygroup',
                    'member':[{"name":"agent_in_group","mbox":"mailto:agentingroup@example.com"}]},
                'contextActivities': {'other': [{'id': 'act:activity1'},{'id':'act:activity2'}],
                'grouping':{'id':'act:activity3'}},'revision': 'foo', 'platform':'bar','language': 'en-US',
                'extensions':{'ext:key1': 'value1'}}}))
        
        stmt2 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url2"},
            "object": {'id':'act:activity4'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'team':{'objectType': 'Group', 'name':'mygroup',
                    'member':[{"name":"agent_in_group","mbox":"mailto:agentingroup@example.com"}]},
                'contextActivities': {'other': [{'id': 'act:activity2'},{'id':'act:activity3'}],
                'grouping':{'id':'act:activity5'}},'revision': 'foo', 'platform':'bar','language': 'en-US'}}))

        stmt3 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url3"},
            "object": {'id':'act:activity1'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:three@inst.com'},
                'team':{'objectType': 'Group', 'name':'mygroup',
                    'member':[{"name":"agent_in_group","mbox":"mailto:agentingroup@example.com"}]},
                'contextActivities': {'other': [{'id': 'act:activity6'},{'id':'act:activity5'}],
                'grouping':{'id':'act:activity2'}},'revision': 'three', 'platform':'bar','language': 'en-US'}}))

        self.assertEqual(len(models.Activity.objects.all()), 6)
        self.assertEqual(len(models.Agent.objects.all()), 7)
        self.assertEqual(len(models.Verb.objects.all()), 3)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 6)
        self.assertEqual(len(models.Statement.objects.all()), 3)

        models.Statement.objects.get(id=stmt3.model_object.id).delete()
        # Agents/activities/verbs are not deleted
        self.assertEqual(len(models.Activity.objects.all()), 6)
        self.assertEqual(len(models.Agent.objects.all()), 7)        
        self.assertEqual(len(models.Verb.objects.all()), 3)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 4)
        self.assertEqual(len(models.Statement.objects.all()), 2)

        models.Statement.objects.get(id=stmt2.model_object.id).delete()
        self.assertEqual(len(models.Activity.objects.all()), 6)
        self.assertEqual(len(models.Agent.objects.all()), 7)        
        self.assertEqual(len(models.Verb.objects.all()), 3)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 2)
        self.assertEqual(len(models.Statement.objects.all()), 1)

        models.Statement.objects.get(id=stmt1.model_object.id).delete()
        self.assertEqual(len(models.Activity.objects.all()), 6)
        self.assertEqual(len(models.Agent.objects.all()), 7)        
        self.assertEqual(len(models.Verb.objects.all()), 3)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 0)
        self.assertEqual(len(models.Statement.objects.all()), 0)

    def test_simple_statement_delete(self):
        stmt1 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'}}))
        
        stmt2 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:b@b.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'}}))

        self.assertEqual(len(models.Agent.objects.all()), 2)
        self.assertEqual(len(models.Activity.objects.all()), 1)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Statement.objects.all()), 2)

        models.Statement.objects.get(id=stmt2.model_object.id).delete()

        self.assertEqual(len(models.Agent.objects.all()), 2)
        self.assertEqual(len(models.Activity.objects.all()), 1)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Statement.objects.all()), 1)
        self.assertEqual(models.Statement.objects.all()[0].id, stmt1.model_object.id)

    def test_more_conacts_delete(self):
        stmt1 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'}}))

        stmt2 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity2'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'contextActivities': {'other': {'id': 'act:activity1'}},'revision': 'foo', 'platform':'bar',
                'language': 'en-US'}}))

        self.assertEqual(len(models.Agent.objects.all()), 2)
        self.assertEqual(len(models.Activity.objects.all()), 2)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Statement.objects.all()), 2)

        models.Statement.objects.get(id=stmt2.model_object.id).delete()

        self.assertEqual(len(models.Agent.objects.all()), 2)
        self.assertEqual(len(models.Activity.objects.all()), 2)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Statement.objects.all()), 1)

    def test_activity_also_in_conact(self):
        stmt1 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'contextActivities': {'other': {'id': 'act:activity2'}},'revision': 'foo', 'platform':'bar',
                'language': 'en-US'}}))

        stmt2 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity2'}}))

        self.assertEqual(len(models.Agent.objects.all()), 2)
        self.assertEqual(len(models.Activity.objects.all()), 2)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.Statement.objects.all()), 2)

        models.Statement.objects.get(id=stmt2.model_object.id).delete()

        self.assertEqual(len(models.Agent.objects.all()), 2)
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
        self.assertEqual(models.Statement.objects.all()[0].id, stmt1.model_object.id)

    def test_sub_delete(self):
        stmt1 = StatementManager(json.dumps(
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
                    "platform":"bar","language": "en-US","extensions":{"ext:k1": "v1", "ext:k2": "v2"}}}}))

        stmt2 = StatementManager(json.dumps(
            {"actor": {"objectType": "Agent", "mbox": "mailto:ref@ref.com"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/2"},
            "object":{"objectType": "StatementRef", "id":str(stmt1.model_object.statement_id)}}))

        stmt3 = StatementManager(json.dumps(
            {"actor": {"objectType": "Agent", "mbox": "mailto:norm@norm.com"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/3"},
            "object":{"objectType": "Activity", "id":"act:activity1"}}))

        stmt4 = StatementManager(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/4"},
            "object": {'id':'act:activity2'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'contextActivities': {'other': {'id': 'act:conactivity1'}},'revision': 'foo', 'platform':'bar',
                'language': 'en-US', 'statement':{'objectType': 'StatementRef',
                'id':str(stmt3.model_object.statement_id)}}}))


        self.assertEqual(len(models.Statement.objects.all()), 4)
        self.assertEqual(len(models.Agent.objects.all()), 8)
        self.assertEqual(len(models.Activity.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 5)
        self.assertEqual(len(models.SubStatement.objects.all()), 1)
        self.assertEqual(len(models.StatementRef.objects.all()), 1)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 1)
        self.assertEqual(len(models.SubStatementContextActivity.objects.all()), 1)
        models.Statement.objects.get(id=stmt4.model_object.id).delete()

        self.assertEqual(len(models.Statement.objects.all()), 3)
        self.assertEqual(len(models.Agent.objects.all()), 8)
        self.assertEqual(len(models.Activity.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 5)
        self.assertEqual(len(models.SubStatement.objects.all()), 1)
        self.assertEqual(len(models.StatementRef.objects.all()), 1)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 0)
        self.assertEqual(len(models.SubStatementContextActivity.objects.all()), 1)
        models.Statement.objects.get(id=stmt3.model_object.id).delete()

        self.assertEqual(len(models.Statement.objects.all()), 2)
        self.assertEqual(len(models.Agent.objects.all()), 8)
        self.assertEqual(len(models.Activity.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 5)
        self.assertEqual(len(models.SubStatement.objects.all()), 1)
        self.assertEqual(len(models.StatementRef.objects.all()), 1)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 0)
        self.assertEqual(len(models.SubStatementContextActivity.objects.all()), 1)
        models.Statement.objects.get(id=stmt2.model_object.id).delete()

        self.assertEqual(len(models.Statement.objects.all()), 1)
        self.assertEqual(len(models.Agent.objects.all()), 8)
        self.assertEqual(len(models.Activity.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 5)
        self.assertEqual(len(models.SubStatement.objects.all()), 1)
        self.assertEqual(len(models.StatementRef.objects.all()), 0)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 0)
        self.assertEqual(len(models.SubStatementContextActivity.objects.all()), 1)
        models.Statement.objects.get(id=stmt1.model_object.id).delete()

        self.assertEqual(len(models.Statement.objects.all()), 0)
        self.assertEqual(len(models.Agent.objects.all()), 8)
        self.assertEqual(len(models.Activity.objects.all()), 5)
        self.assertEqual(len(models.Verb.objects.all()), 5)
        self.assertEqual(len(models.SubStatement.objects.all()), 0)
        self.assertEqual(len(models.StatementRef.objects.all()), 0)
        self.assertEqual(len(models.StatementContextActivity.objects.all()), 0)
        self.assertEqual(len(models.SubStatementContextActivity.objects.all()), 0)
