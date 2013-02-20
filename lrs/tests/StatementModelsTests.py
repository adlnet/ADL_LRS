from django.test import TestCase
from lrs import models
from lrs.exceptions import ParamError, Forbidden, ParamConflict, IDNotFoundError
import json
from datetime import datetime
import uuid
import pdb
from lrs.objects import Statement

def get_ctx_id(stmt):
    if len(stmt.context.all()) > 0:
        return stmt.context.all()[0].id
    return None

class StatementModelsTests(TestCase):
         
    def test_minimum_stmt(self):
        stmt = Statement.Statement(json.dumps({"actor":{"objectType":"Agent","mbox": "tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        verb = models.Verb.objects.get(id=stmt.model_object.verb.id)
        actor = models.agent.objects.get(id=stmt.model_object.actor.id)

        self.assertEqual(activity.activity_id, "http://example.adlnet.gov/tincan/example/simplestatement")
        self.assertEqual(actor.mbox, "tincan@adlnet.gov")
        self.assertEqual(verb.verb_id, "http://adlnet.gov/expapi/verbs/created")


    def test_given_stmtID_stmt(self):
        stmt = Statement.Statement(json.dumps({"statement_id":"blahID",
            "actor":{"objectType":"Agent","mbox": "tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created", "en-GB":"made"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))
        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        verb = models.Verb.objects.get(id=stmt.model_object.verb.id)
        actor = models.agent.objects.get(id=stmt.model_object.actor.id)
        lang_maps = verb.display.all()

        for lm in lang_maps:
            if lm.key == 'en-GB':
                self.assertEqual(lm.value, 'made')
            elif lm.key == 'en-US':
                self.assertEqual(lm.value, 'created')
        
        self.assertEqual(activity.activity_id, "http://example.adlnet.gov/tincan/example/simplestatement")
        self.assertEqual(actor.mbox, "tincan@adlnet.gov")
        self.assertEqual(verb.verb_id, "http://adlnet.gov/expapi/verbs/created")
        
        st = models.statement.objects.get(statement_id="blahID")
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.verb.id, verb.id)


    def test_existing_stmtID_stmt(self):
        stmt = Statement.Statement(json.dumps({"statement_id":"blahID","verb":{"id":"verb:verb/url",
            "display":{"en-US":"myverb"}}, "object": {"id":"activity"}, "actor":{"objectType":"Agent",
            "mbox":"t@t.com"}}))
        self.assertRaises(ParamConflict, Statement.Statement, json.dumps({"statement_id":"blahID",
            "verb":{"id":"verb:verb/url","display":{"en-US":"myverb"}},"object": {'id':'activity2'},
            "actor":{"objectType":"Agent", "mbox":"t@t.com"}}))
        

    def test_voided_stmt(self):
        stmt = Statement.Statement(json.dumps({"actor":{"objectType":"Agent","mbox": "tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))

        st_id = stmt.model_object.statement_id
        st_model = models.statement.objects.get(statement_id=st_id)
        self.assertEqual(st_model.voided, False)

        stmt2 = Statement.Statement(json.dumps({"actor":{"name":"Example Admin", "mbox":"admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/voided"}, 'object': {'objectType':'StatementRef',
            'id': str(st_id)}}))
        
        st_model = models.statement.objects.get(statement_id=st_id)        
        self.assertEqual(st_model.voided, True)

        stmt_ref = models.StatementRef.objects.get(ref_id=str(st_id))
        self.assertEqual(stmt_ref.object_type, 'StatementRef')


    def test_stmt_ref_as_object(self):
        

        stmt = Statement.Statement(json.dumps({"actor":{"objectType":"Agent","mbox": "tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"},
            "statement_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}))

        stmt2 = Statement.Statement(json.dumps({"actor":{"name":"Example Admin", "mbox":"admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/attempted"}, 'object': {'objectType':'StatementRef',
            'id': "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}))

        stmts = models.statement.objects.all()
        stmt_refs = models.StatementRef.objects.filter(ref_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertEqual(len(stmt_refs), 1)
        self.assertEqual(stmt_refs[0].ref_id, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertEqual(len(stmts), 2)

    def test_stmt_ref_no_existing_stmt(self):


        self.assertRaises(IDNotFoundError, Statement.Statement, json.dumps({"actor":{"name":"Example Admin", "mbox":"admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/attempted"}, 'object': {'objectType':'StatementRef',
            'id': "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}))

    def test_voided_wrong_type(self):
        stmt = Statement.Statement(json.dumps({"actor":{"objectType":"Agent","mbox": "tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))

        st_id = stmt.model_object.statement_id

        self.assertRaises(ParamError, Statement.Statement, json.dumps({"actor":{"name":"Example Admin", "mbox":"admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/voided"}, 'object': {'objectType':'Statement',
            'id': str(st_id)}}))


    def test_no_verb_stmt(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"actor":{"objectType":"Agent", "mbox":"t@t.com"},
            "object": {'id':'activity2'}}))


    def test_no_object_stmt(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"actor":{"objectType":"Agent", "mbox":"t@t.com"},
            "verb": {"id":"verb:verb/url"}}))


    def test_no_actor_stmt(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"object":{"id":"activity_test"},
            "verb": {"id":"verb:verb/url"}}))


    def test_not_json_stmt(self):
        self.assertRaises(ParamError, Statement.Statement, "This will fail.")


    def test_voided_true_stmt(self):
        self.assertRaises(Forbidden, Statement.Statement, json.dumps({'actor':{'objectType':'Agent', 'mbox':'l@l.com'},
            'verb': {"id":'verb:verb/url/kicked'},'voided': True,
            'object': {'id':'activity3'}}))


    def test_contradictory_completion_result_stmt(self):
    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'activity4'},"result":{"completion": False}}))

    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'activity5'},"result":{"completion": False}}))

    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'activity6'},"result":{"completion": False}}))
    	
    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"}
            ,"object": {'id':'activity7'},"result":{"completion": False}})) 

		
    def test_contradictory_success_result_stmt(self):
    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'activity8'},"result":{"success": False}}))
    	
    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'activity9'},"result":{"success": False}}))
    	
    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'activity10'},"result":{"success": True}})) 

    def test_result_stmt(self):
        time = "P0Y0M0DT1H311M01S"
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'s@s.com'}, 
            'verb': {"id":"verb:verb/url"},"object": {'id':'activity12'},
            "result": {'completion': True, 'success': True, 'response': 'kicked', 'duration': time}}))
        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        self.assertEqual(len(stmt.model_object.result.all()), 1)
        resid = stmt.model_object.result.all()[0].id
        result = models.result.objects.get(id=resid)

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.stmt_object.id, activity.id)
        self.assertEqual(stmt.model_object.result.all()[0].id, result.id)

        st = models.statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.result.all()[0].id, result.id)

        self.assertEqual(result.completion, True)
        self.assertEqual(result.success, True)
        self.assertEqual(result.response, 'kicked')
        self.assertEqual(result.duration, time)

    def test_result__wrong_duration_stmt(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({'actor':{'objectType':'Agent','mbox':'s@s.com'}, 
            'verb': {"id":"verb:verb/url"},"object": {'id':'activity12'},
            "result": {'completion': True, 'success': True, 'response': 'kicked', 'duration': 'notright'}}))

    def test_result_ext_stmt(self):
        time = "P0Y0M0DT1H311M01S"
        stmt = Statement.Statement(json.dumps({"actor":{'objectType':'Person','name':'jon',
            'mbox':'jon@example.com'},'verb': {"id":"verb:verb/url"},"object": {'id':'activity13'}, 
            "result": {'completion': True, 'success': True, 'response': 'yes', 'duration': time,
            'extensions':{'ext:key1': 'value1', 'ext:key2':'value2'}}}))
        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        self.assertEqual(len(stmt.model_object.result.all()), 1)
        resid = stmt.model_object.result.all()[0].id
        result = models.result.objects.get(id=resid)
        actor = models.agent.objects.get(id=stmt.model_object.actor.id)
        extList = result.extensions.values_list()
        extKeys = [ext[1] for ext in extList]
        extVals = [ext[2] for ext in extList]

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.stmt_object.id, activity.id)
        self.assertEqual(stmt.model_object.result.all()[0].id, result.id)
        self.assertEqual(stmt.model_object.actor.id, actor.id)

        st = models.statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.result.all()[0].id, result.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(result.completion, True)
        self.assertEqual(result.success, True)
        self.assertEqual(result.response, 'yes')
        self.assertEqual(result.duration, time)

        self.assertEqual(actor.name, 'jon')
        self.assertEqual(actor.mbox, 'jon@example.com')

        self.assertIn('ext:key1', extKeys)
        self.assertIn('ext:key2', extKeys)
        self.assertIn('value1', extVals)
        self.assertIn('value2', extVals)


    def test_result_score_stmt(self):
        time = "P0Y0M0DT1H311M01S"
        stmt = Statement.Statement(json.dumps({"actor":{'objectType':'Agent','name':'jon','mbox':'jon@example.com'},
            'verb': {"id":"verb:verb/url"},"object": {'id':'activity14'}, "result": {'score':{'scaled':.95},
            'completion': True, 'success': True, 'response': 'yes', 'duration': time,
            'extensions':{'ext:key1': 'value1', 'ext:key2':'value2'}}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        self.assertEqual(len(stmt.model_object.result.all()), 1)
        resid = stmt.model_object.result.all()[0].id
        result = models.result.objects.get(id=resid)
        score = models.score.objects.get(id=stmt.model_object.result.all()[0].score.id)
        actor = models.agent.objects.get(id=stmt.model_object.actor.id)
        extList = result.extensions.values_list()
        extKeys = [ext[1] for ext in extList]
        extVals = [ext[2] for ext in extList]

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.stmt_object.id, activity.id)
        self.assertEqual(stmt.model_object.result.all()[0].id, result.id)
        self.assertEqual(stmt.model_object.actor.id, actor.id)

        st = models.statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.result.all()[0].id, result.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(result.completion, True)
        self.assertEqual(result.success, True)
        self.assertEqual(result.response, 'yes')
        self.assertEqual(result.duration, time)
        self.assertEqual(result.score.id, score.id)

        self.assertEqual(score.scaled, .95)

        self.assertEqual(activity.activity_id, 'activity14')

        self.assertEqual(actor.name, 'jon')
        self.assertEqual(actor.mbox, 'jon@example.com')

        self.assertIn('ext:key1', extKeys)
        self.assertIn('ext:key2', extKeys)
        self.assertIn('value1', extVals)
        self.assertIn('value2', extVals)


    def test_no_registration_context_stmt(self):
        # expect the LRS to assign a context registration uuid
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'s@s.com'},"verb":{"id":"verb:verb/url"},"object": {'id':'activity14'},
                         'context': {'contextActivities': {'other': {'id': 'NewActivityID'}}}})).model_object
        ctxid = get_ctx_id(stmt)
        context = models.context.objects.get(id=ctxid)
        self.assertIsNotNone(context.registration)   


    def test_context_stmt(self):
        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'activity15'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'NewActivityID'}, 'grouping':{'id':'GroupID'}},
                'revision': 'foo', 'platform':'bar',
                'language': 'en-US'}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        context_activities = stmt.model_object.context.all()[0].contextactivity_set.all()

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.stmt_object.id, activity.id)
        self.assertEqual(ctxid, context.id)

        st = models.statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.all()[0].id, context.id)
        
        for ca in context_activities:
            if ca.key == 'grouping':
                self.assertEqual(ca.context_activity, 'GroupID')
            elif ca.key == 'other':
                self.assertEqual(ca.context_activity, 'NewActivityID')

        self.assertEqual(context.registration, guid)        
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')


    def test_context_ext_stmt(self):
        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'activity16'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US', 'extensions':{'ext:k1': 'v1', 'ext:k2': 'v2'}}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        extList = context.extensions.values_list()
        extKeys = [ext[1] for ext in extList]
        extVals = [ext[2] for ext in extList]
        context_activities = stmt.model_object.context.all()[0].contextactivity_set.all()

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.stmt_object.id, activity.id)
        self.assertEqual(ctxid, context.id)

        st = models.statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.all()[0].id, context.id)

        self.assertEqual(context.registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].context_activity, 'NewActivityID')
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')

        self.assertIn('ext:k1', extKeys)
        self.assertIn('ext:k2', extKeys)
        self.assertIn('v1', extVals)
        self.assertIn('v2', extVals)


    def test_stmt_in_context_stmt(self):
        stmt_guid = str(uuid.uuid4())

        existing_stmt = Statement.Statement(json.dumps({'statement_id':stmt_guid, 'actor':{'objectType':'Agent','mbox':'s@s.com'},
            'verb': {"id":"verb:verb/url/outer"},"object": {'id':'activityy16'}}))

        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'activity16'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US', 'statement': {'id': stmt_guid}}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.statement.objects.get(statement_id=stmt_ref.ref_id)

        st = models.statement.objects.get(id=stmt.model_object.id)

        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.all()[0].id, context.id)

        self.assertEqual(context.registration, guid)

        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")


    def test_instructor_in_context_stmt(self):
        stmt_guid = str(uuid.uuid4())
        existing_stmt = Statement.Statement(json.dumps({'statement_id':stmt_guid, 'actor':{'objectType':'Agent','mbox':'s@s.com'},
            'verb': {"id":"verb:verb/url/outer"},"object": {'id':'activityy16'}}))

        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'jon@example.com', 'name':'jon'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'activity17'},
                'context':{'registration': guid, 'instructor': {'objectType':'Agent',
                'name':'jon','mbox':'jon@example.com'},'contextActivities': {'other': {'id': 'NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US', 'statement': {'id': stmt_guid}}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        conactor = models.agent.objects.get(id=stmt.model_object.context.all()[0].instructor.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.statement.objects.get(statement_id=stmt_ref.ref_id)
        context_activities = stmt.model_object.context.all()[0].contextactivity_set.all()

        st = models.statement.objects.get(id=stmt.model_object.id)

        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.all()[0].id, context.id)
        self.assertEqual(st.context.all()[0].instructor.id, conactor.id)

        self.assertEqual(context.registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].context_activity, 'NewActivityID')
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')
        
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")
        
        self.assertEqual(conactor.objectType, 'Agent')
        
        self.assertEqual(conactor.name, 'jon')
        self.assertEqual(conactor.mbox, 'jon@example.com') 


    def test_actor_with_context_stmt(self):
        stmt_guid = str(uuid.uuid4())
        existing_stmt = Statement.Statement(json.dumps({'statement_id':stmt_guid, 'actor':{'objectType':'Agent','mbox':'s@s.com'},
            'verb': {"id":"verb:verb/url/outer"},"object": {'id':'activityy16'}}))

        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent', 'name': 'steve', 'mbox':'s@s.com'},
            'verb': {"id":"verb:verb/url"},"object": {'id':'activity18'},'context':{'registration': guid, 
            'instructor': {'objectType':'Agent','name':'jon','mbox':'jon@example.com'},
            'contextActivities': {'other': {'id': 'NewActivityID1'}}, 'revision': 'foob', 'platform':'bard',
            'language': 'en-US', 'statement': {'id':stmt_guid}}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        instructor = models.agent.objects.get(id=stmt.model_object.context.all()[0].instructor.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.statement.objects.get(statement_id=stmt_ref.ref_id)
        st = models.statement.objects.get(id=stmt.model_object.id)
        context_activities = stmt.model_object.context.all()[0].contextactivity_set.all()

        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.all()[0].id, context.id)
        self.assertEqual(st.context.all()[0].instructor.id, instructor.id)
        self.assertEqual(st.verb.verb_id, "verb:verb/url" )

        self.assertEqual(context.registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].context_activity, 'NewActivityID1')
        self.assertEqual(context.revision, 'foob')
        self.assertEqual(context.platform, 'bard')
        self.assertEqual(context.language, 'en-US')
        
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")
        
        self.assertEqual(instructor.objectType, 'Agent')
        
        self.assertEqual(instructor.name, 'jon')
        self.assertEqual(instructor.mbox, 'jon@example.com') 


    def test_agent_as_object_with_context_stmt(self):
        stmt_guid = str(uuid.uuid4())
        existing_stmt = Statement.Statement(json.dumps({'statement_id':stmt_guid, 'actor':{'objectType':'Agent','mbox':'s@s.com'},
            'verb': {"id":"verb:verb/url/outer"},"object": {'id':'activityy16'}}))

        guid = str(uuid.uuid4())
        stmt = Statement.Statement(
            json.dumps(
                {'actor':{
                'objectType':'Agent',
                'mbox':'l@l.com',
                'name':'lou'
                },
                'object':{
                    'objectType':'Agent', 
                    'name': 'lou', 
                    'mbox':'l@l.com'
                 }, 
                 'verb': {"id":"verb:verb/url"},
                 'context':{
                    'registration': guid, 
                    'instructor': {
                        'objectType':'Agent',
                        'name':'jon',
                        'mbox':'jon@example.com'
                    },
                    'contextActivities': {
                        'other': {'id': 'NewActivityID1'}
                    }, 
                    'revision': 'foob', 
                    'platform':'bard',
                    'language': 'en-US', 
                    'statement': {
                        'id': stmt_guid
                    }
                 }
                }
            )
        )

        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        instructor = models.agent.objects.get(id=stmt.model_object.context.all()[0].instructor.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.statement.objects.get(statement_id=stmt_ref.ref_id)
        context_activities = stmt.model_object.context.all()[0].contextactivity_set.all()

        st = models.statement.objects.get(id=stmt.model_object.id)

        self.assertEqual(st.context.all()[0].id, context.id)
        self.assertEqual(st.context.all()[0].instructor.id, instructor.id)
        self.assertEqual(st.verb.verb_id, "verb:verb/url")

        self.assertEqual(context.registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].context_activity, 'NewActivityID1')
        self.assertEqual(context.language, 'en-US')
        
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")
        
        self.assertEqual(instructor.objectType, 'Agent')
        
        # Should be jon
        self.assertEqual(instructor.name, 'jon')
        self.assertEqual(instructor.mbox, 'jon@example.com') 


    def test_agent_as_object(self):
        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({'object':{'objectType':'Agent', 'name': 'lulu', 'openid':'luluid'}, 
            'verb': {"id":"verb:verb/url"},'actor':{'objectType':'Agent','mbox':'t@t.com'}}))

        st = models.statement.objects.get(id=stmt.model_object.id)
        agent = models.agent.objects.get(id=stmt.model_object.stmt_object.id)

        self.assertEqual(agent.name, 'lulu')
        self.assertEqual(agent.openid, 'luluid')


    def test_unallowed_substmt_field(self):
        stmt = {'actor':{'objectType':'Agent','mbox':'s@s.com'},
            'verb': {"id":"verb:verb/url"}, 'object':{'objectType':'SubStatement',
            'actor':{'objectType':'Agent','mbox':'ss@ss.com'},'verb': {"id":"verb:verb/url/nest"},
            'object': {'objectType':'activity', 'id':'testex.com'},
            'authority':{'objectType':'Agent','mbox':'s@s.com'}}}
        self.assertRaises(ParamError, Statement.Statement, json.dumps(stmt))


    def test_nested_substatement(self):
        stmt = {'actor':{'objectType':'Agent','mbox':'s@s.com'},
            'verb': {"id":"verb:verb/url"}, 'object':{'objectType':'SubStatement',
            'actor':{'objectType':'Agent','mbox':'ss@ss.com'},'verb': {"id":"verb:verb/url/nest"},
            'object': {'objectType':'SubStatement', 'actor':{'objectType':'Agent','mbox':'sss@sss.com'},
            'verb':{'id':'verb:verb/url/nest/nest'}, 'object':{'id':'activity/url'}}}}
        self.assertRaises(ParamError, Statement.Statement, json.dumps(stmt))


    def test_substatement_as_object(self):
        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'s@s.com'},
            'verb': {"id":"verb:verb/url"}, 'object':{'objectType':'SubStatement',
            'actor':{'objectType':'Agent','mbox':'ss@ss.com'},'verb': {"id":"verb:verb/url/nest"},
            'object': {'objectType':'activity', 'id':'testex.com'}, 'result':{'completion': True, 'success': True,
            'response': 'kicked'}, 'context':{'registration': guid,
            'contextActivities': {'other': {'id': 'NewActivityID'}},'revision': 'foo', 'platform':'bar',
            'language': 'en-US', 'extensions':{'ext:k1': 'v1', 'ext:k2': 'v2'}}}}))

        outer_stmt = models.statement.objects.get(id=stmt.model_object.id)
        sub_stmt = models.SubStatement.objects.get(id=outer_stmt.stmt_object.id)
        sub_obj = models.activity.objects.get(id=sub_stmt.stmt_object.id)
        sub_act = models.agent.objects.get(id=sub_stmt.actor.id)
        sub_con = models.context.objects.get(id=sub_stmt.context.all()[0].id)
        self.assertEqual(len(sub_stmt.result.all()), 1)
        resid = sub_stmt.result.all()[0].id
        sub_res = models.result.objects.get(id=resid)

        self.assertEqual(outer_stmt.verb.verb_id, "verb:verb/url")
        self.assertEqual(outer_stmt.actor.mbox, 's@s.com')        
        self.assertEqual(sub_stmt.verb.verb_id, "verb:verb/url/nest")
        self.assertEqual(sub_obj.activity_id, 'testex.com')
        self.assertEqual(sub_act.mbox, 'ss@ss.com')
        self.assertEqual(sub_con.registration, guid)
        self.assertEqual(sub_res.response, 'kicked')
        

    def test_model_authoritative_set(self):
        stmt = Statement.Statement(json.dumps({"actor":{"name":"tom","mbox":"mailto:tom@example.com"},
            'verb': {"id":"verb:verb/url"}, "object": {"id":"activity"}}))
        self.assertTrue(models.statement.objects.get(pk=stmt.model_object.pk).authoritative)
        
        stmt2 = Statement.Statement(json.dumps({"actor":{"name":"tom","mbox":"mailto:tom@example.com"},
            'verb': {"id":"verb:verb/url"}, "object": {"id":"activity"}}))
        self.assertTrue(models.statement.objects.get(pk=stmt2.model_object.pk).authoritative)
        self.assertFalse(models.statement.objects.get(pk=stmt.model_object.pk).authoritative)
        
        stmt3 = Statement.Statement(json.dumps({"actor":{"name":"tom","mbox":"mailto:tom@example.com"},
            'verb': {"id":"verb:verb/url"}, "object": {"id":"activity2"}}))

        self.assertTrue(models.statement.objects.get(pk=stmt3.model_object.pk).authoritative)
        self.assertTrue(models.statement.objects.get(pk=stmt2.model_object.pk).authoritative)
        self.assertFalse(models.statement.objects.get(pk=stmt.model_object.pk).authoritative)


    def test_group_stmt(self):
        ot = "Group"
        name = "the group SMT"
        mbox = "mailto:the.groupSMT@example.com"
        members = [{"name":"agentA","mbox":"mailto:agentA@example.com"},
                    {"name":"agentB","mbox":"mailto:agentB@example.com"}]
        testagent = json.dumps({"objectType":ot, "name":name, "mbox":mbox,"member":members})
        
        stmt = Statement.Statement(json.dumps({"actor":testagent, 'verb': {"id":"verb:verb/url"},"object": {"id":"activity5",
            "objectType": "Activity"}}))
        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        actor = models.agent.objects.get(id=stmt.model_object.actor.id)

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.stmt_object.id, activity.id)
        self.assertEqual(stmt.model_object.actor.id, actor.id)

        st = models.statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(actor.name, name)
        self.assertEqual(actor.mbox, mbox)
