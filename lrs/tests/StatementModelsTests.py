from django.test import TestCase
from lrs import models
from lrs.exceptions import ParamError, Forbidden, ParamConflict, IDNotFoundError
import json
from datetime import datetime
import uuid
import pdb
from lrs.objects import Statement, Activity

def get_ctx_id(stmt):
    if stmt.context:
        return stmt.context.id
    return None

class StatementModelsTests(TestCase):
         
    def test_minimum_stmt(self):
        stmt = Statement.Statement(json.dumps({"actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        verb = models.Verb.objects.get(id=stmt.model_object.verb.id)
        actor = models.agent.objects.get(id=stmt.model_object.actor.id)

        self.assertEqual(activity.activity_id, "http://example.adlnet.gov/tincan/example/simplestatement")
        self.assertEqual(actor.mbox, "mailto:tincan@adlnet.gov")
        self.assertEqual(verb.verb_id, "http://adlnet.gov/expapi/verbs/created")


    def test_given_stmtID_stmt(self):
        st_id = str(uuid.uuid1())
        stmt = Statement.Statement(json.dumps({"statement_id":st_id,
            "actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
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
        self.assertEqual(actor.mbox, "mailto:tincan@adlnet.gov")
        self.assertEqual(verb.verb_id, "http://adlnet.gov/expapi/verbs/created")
        
        st = models.statement.objects.get(statement_id=st_id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.verb.id, verb.id)


    def test_existing_stmtID_stmt(self):
        st_id = str(uuid.uuid1())
        stmt = Statement.Statement(json.dumps({"statement_id":st_id,"verb":{"id":"verb:verb/url",
            "display":{"en-US":"myverb"}}, "object": {"id":"act:activity"}, "actor":{"objectType":"Agent",
            "mbox":"mailto:t@t.com"}}))
        self.assertRaises(ParamConflict, Statement.Statement, json.dumps({"statement_id":st_id,
            "verb":{"id":"verb:verb/url","display":{"en-US":"myverb"}},"object": {'id':'act:activity2'},
            "actor":{"objectType":"Agent", "mbox":"mailto:t@t.com"}}))
        
    def test_invalid_stmtID(self):
        st_id = "aaa"
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"statement_id":st_id,
            "verb":{"id":"verb:verb/url","display":{"en-US":"myverb"}},"object": {'id':'act:activity2'},
            "actor":{"objectType":"Agent", "mbox":"mailto:t@t.com"}}))

    def test_voided_stmt(self):
        stmt = Statement.Statement(json.dumps({"actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))

        st_id = stmt.model_object.statement_id
        st_model = models.statement.objects.get(statement_id=st_id)
        self.assertEqual(st_model.voided, False)

        stmt2 = Statement.Statement(json.dumps({"actor":{"name":"Example Admin", "mbox":"mailto:admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/voided"}, 'object': {'objectType':'StatementRef',
            'id': str(st_id)}}))
        
        st_model = models.statement.objects.get(statement_id=st_id)        
        self.assertEqual(st_model.voided, True)

        stmt_ref = models.StatementRef.objects.get(ref_id=str(st_id))
        self.assertEqual(stmt_ref.object_type, 'StatementRef')


    def test_stmt_ref_as_object(self):
        st_id = str(uuid.uuid1())

        stmt = Statement.Statement(json.dumps({"actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"},
            "statement_id":st_id}))

        stmt2 = Statement.Statement(json.dumps({"actor":{"name":"Example Admin", "mbox":"mailto:admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/attempted"}, 'object': {'objectType':'StatementRef',
            'id': st_id}}))

        stmts = models.statement.objects.all()
        stmt_refs = models.StatementRef.objects.filter(ref_id=st_id)
        self.assertEqual(len(stmt_refs), 1)
        self.assertEqual(stmt_refs[0].ref_id, st_id)
        self.assertEqual(len(stmts), 2)

    def test_stmt_ref_no_existing_stmt(self):


        self.assertRaises(IDNotFoundError, Statement.Statement, json.dumps({"actor":{"name":"Example Admin", "mbox":"mailto:admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/attempted"}, 'object': {'objectType':'StatementRef',
            'id': "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}))

    def test_voided_wrong_type(self):
        stmt = Statement.Statement(json.dumps({"actor":{"objectType":"Agent","mbox": "mailto:tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))

        st_id = stmt.model_object.statement_id

        self.assertRaises(ParamError, Statement.Statement, json.dumps({"actor":{"name":"Example Admin", "mbox":"mailto:admin@example.com"},
            'verb': {"id":"http://adlnet.gov/expapi/verbs/voided"}, 'object': {'objectType':'Statement',
            'id': str(st_id)}}))


    def test_no_verb_stmt(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"actor":{"objectType":"Agent", "mbox":"mailto:t@t.com"},
            "object": {'id':'act:activity2'}}))


    def test_no_object_stmt(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"actor":{"objectType":"Agent", "mbox":"mailto:t@t.com"},
            "verb": {"id":"verb:verb/url"}}))


    def test_no_actor_stmt(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"object":{"id":"act:activity_test"},
            "verb": {"id":"verb:verb/url"}}))


    def test_not_json_stmt(self):
        self.assertRaises(ParamError, Statement.Statement, "This will fail.")


    def test_voided_true_stmt(self):
        self.assertRaises(Forbidden, Statement.Statement, json.dumps({'actor':{'objectType':'Agent', 'mbox':'mailto:l@l.com'},
            'verb': {"id":'verb:verb/url/kicked'},'voided': True,
            'object': {'id':'act:activity3'}}))


    def test_contradictory_completion_result_stmt(self):
    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity4'},"result":{"completion": False}}))

    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity5'},"result":{"completion": False}}))

    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity6'},"result":{"completion": False}}))
    	
    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"}
            ,"object": {'id':'act:act:activity7'},"result":{"completion": False}})) 

		
    def test_contradictory_success_result_stmt(self):
    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity8'},"result":{"success": False}}))
    	
    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity9'},"result":{"success": False}}))
    	
    	self.assertRaises(ParamError, Statement.Statement, json.dumps({'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity10'},"result":{"success": True}})) 

    def test_result_stmt(self):
        time = "P0Y0M0DT1H311M01S"
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'}, 
            'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity12'},
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
        self.assertRaises(ParamError, Statement.Statement, json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'}, 
            'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity12'},
            "result": {'completion': True, 'success': True, 'response': 'kicked', 'duration': 'notright'}}))

    def test_result_ext_stmt(self):
        time = "P0Y0M0DT1H311M01S"
        stmt = Statement.Statement(json.dumps({"actor":{'objectType':'Person','name':'jon',
            'mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity13'}, 
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
        self.assertEqual(actor.mbox, 'mailto:jon@example.com')

        self.assertIn('ext:key1', extKeys)
        self.assertIn('ext:key2', extKeys)
        self.assertIn('value1', extVals)
        self.assertIn('value2', extVals)

    def test_result_score_scaled_up_good(self):
        Statement.Statement(json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'scaled':1.0},'completion': True,
            'success': True, 'response': 'yes'}}))

    def test_result_score_scaled_down_good(self):
        Statement.Statement(json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'scaled':00.000},'completion': True,
            'success': True, 'response': 'yes'}}))

    def test_result_score_scaled_up_bad(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'scaled':1.01},'completion': True,
            'success': True, 'response': 'yes'}}))

    def test_result_score_scaled(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'scaled':-1.00001},'completion': True,
            'success': True, 'response': 'yes'}}))

    def test_result_score_raw_up_good(self):
        Statement.Statement(json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'raw':1.01,'min':-2.0, 'max':1.01},
            'completion': True,'success': True, 'response': 'yes'}}))

    def test_result_score_raw_down_good(self):
        Statement.Statement(json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'raw':-20.0,'min':-20.0, 'max':1.01},
            'completion': True,'success': True, 'response': 'yes'}}))

    def test_result_score_raw_up_bad(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'raw':1.02,'min':-2.0, 'max':1.01},
            'completion': True,'success': True, 'response': 'yes'}}))

    def test_result_score_raw_down_bad(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'raw':-2.00001,'min':-2.0, 'max':1.01},
            'completion': True,'success': True, 'response': 'yes'}}))

    def test_result_score_min_max_bad(self):
        self.assertRaises(ParamError, Statement.Statement, json.dumps({"actor":{'objectType':'Agent',
            'name':'jon','mbox':'mailto:jon@example.com'},'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity14'}, "result": {'score':{'raw':1.5,'min':2.0, 'max':1.01},
            'completion': True,'success': True, 'response': 'yes'}}))

    def test_result_score_stmt(self):
        time = "P0Y0M0DT1H311M01S"
        stmt = Statement.Statement(json.dumps({"actor":{'objectType':'Agent','name':'jon','mbox':'mailto:jon@example.com'},
            'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity14'}, "result": {'score':{'scaled':.95},
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

        self.assertEqual(activity.activity_id, 'act:activity14')

        self.assertEqual(actor.name, 'jon')
        self.assertEqual(actor.mbox, 'mailto:jon@example.com')

        self.assertIn('ext:key1', extKeys)
        self.assertIn('ext:key2', extKeys)
        self.assertIn('value1', extVals)
        self.assertIn('value2', extVals)


    def test_no_registration_context_stmt(self):
        # expect the LRS to assign a context registration uuid
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},"verb":{"id":"verb:verb/url"},"object": {'id':'act:activity14'},
                         'context': {'contextActivities': {'other': {'id': 'act:NewActivityID'}}}})).model_object
        ctxid = get_ctx_id(stmt)
        context = models.context.objects.get(id=ctxid)
        self.assertIsNotNone(context.registration)   

    def test_wrong_statement_type_in_context(self):
        self.assertRaises(ParamError, Statement.Statement,json.dumps({'actor':{'objectType':'Agent',
            'mbox':'mailto:s@s.com'},'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity16'},
            'context':{'contextActivities': {'other': {'id': 'act:NewActivityID'}},
            'revision': 'foo', 'platform':'bar','language': 'en-US',
            'statement': {'objectType': 'Activity','id': "act:some/act"}}}))

    def test_invalid_context_registration(self):
        guid = "bbb"
        self.assertRaises(ParamError, Statement.Statement, json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity15'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'act:NewActivityID'}, 'grouping':{'id':'act:GroupID'}},
                'revision': 'foo', 'platform':'bar',
                'language': 'en-US'}}))

    def test_context_stmt(self):
        guid = str(uuid.uuid1())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity15'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'act:NewActivityID'},
                'grouping':{'id':'act:GroupID'}},'revision': 'foo', 'platform':'bar','language': 'en-US'}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        context_activities = stmt.model_object.context.contextactivity_set.all()

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.stmt_object.id, activity.id)
        self.assertEqual(ctxid, context.id)

        st = models.statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)
        
        for ca in context_activities:
            if ca.key == 'grouping':
                self.assertEqual(ca.get_context_activities()[0].activity_id, 'act:GroupID')
            elif ca.key == 'other':
                self.assertEqual(ca.get_context_activities()[0].activity_id, 'act:NewActivityID')

        self.assertEqual(context.registration, guid)        
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')

    def test_context_activity_list(self):
        guid = str(uuid.uuid1())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity15'},
                'context':{'registration': guid,
                'contextActivities': {'other': [{'id': 'act:NewActivityID'},{'id':'act:anotherActID'}],
                'grouping':{'id':'act:GroupID'}},
                'revision': 'foo', 'platform':'bar',
                'language': 'en-US'}}))
        
        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)

        context_activities = models.ContextActivity.objects.filter(context=context)
        self.assertEqual(len(context_activities), 2)
        
        context_activity_keys = [ca.key for ca in context_activities]
        self.assertEqual(len(context_activity_keys), 2)
        self.assertIn('grouping', context_activity_keys)
        self.assertIn('other', context_activity_keys)

        context_activity_activities = []        
        for ca in context_activities:
            for c in ca.get_context_activities():
                context_activity_activities.append(c.activity_id)

        self.assertEqual(len(context_activity_activities), 3)

        self.assertIn('act:NewActivityID', context_activity_activities)
        self.assertIn('act:anotherActID', context_activity_activities)
        self.assertIn('act:GroupID', context_activity_activities)

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.stmt_object.id, activity.id)
        self.assertEqual(ctxid, context.id)

        st = models.statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)

        self.assertEqual(context.registration, guid)        
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')

    def test_context_ext_stmt(self):
        guid = str(uuid.uuid1())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity16'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'act:NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US', 'extensions':{'ext:k1': 'v1', 'ext:k2': 'v2'}}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        extList = context.extensions.values_list()
        extKeys = [ext[1] for ext in extList]
        extVals = [ext[2] for ext in extList]
        context_activities = stmt.model_object.context.contextactivity_set.all()

        self.assertEqual(stmt.model_object.verb.verb_id, "verb:verb/url")
        self.assertEqual(stmt.model_object.stmt_object.id, activity.id)
        self.assertEqual(ctxid, context.id)

        st = models.statement.objects.get(id=stmt.model_object.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)

        self.assertEqual(context.registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].get_context_activities()[0].activity_id, 'act:NewActivityID')
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')

        self.assertIn('ext:k1', extKeys)
        self.assertIn('ext:k2', extKeys)
        self.assertIn('v1', extVals)
        self.assertIn('v2', extVals)


    def test_stmtref_in_context_stmt(self):
        stmt_guid = str(uuid.uuid1())

        existing_stmt = Statement.Statement(json.dumps({'statement_id':stmt_guid, 'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
            'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}}))

        guid = str(uuid.uuid1())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity16'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'act:NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US',
                'statement': {'objectType': 'StatementRef','id': stmt_guid}}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.statement.objects.get(statement_id=stmt_ref.ref_id)

        st = models.statement.objects.get(id=stmt.model_object.id)

        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)

        self.assertEqual(context.registration, guid)

        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')
        self.assertEqual(stmt_ref.ref_id, stmt_guid)
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")

    def test_substmt_in_context_stmt(self):
        stmt_guid = str(uuid.uuid1())

        guid = str(uuid.uuid1())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
                'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity16'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'act:NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US',
                'statement': {'objectType':'SubStatement', 'actor':{'objectType':'Agent',
                'mbox':'mailto:sss@sss.com'},'verb':{'id':'verb:verb/url/nest/nest'},
                'object':{'id':'act://activity/url'}}}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        sub_stmt = models.SubStatement.objects.get(id=context.statement.all()[0].id)

        st = models.statement.objects.get(id=stmt.model_object.id)

        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)

        self.assertEqual(context.registration, guid)
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')
        self.assertEqual(sub_stmt.verb.verb_id, "verb:verb/url/nest/nest")

    def test_instructor_in_context_stmt(self):
        stmt_guid = str(uuid.uuid1())
        existing_stmt = Statement.Statement(json.dumps({'statement_id':stmt_guid, 'actor':{'objectType':'Agent',
            'mbox':'mailto:s@s.com'},'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}}))

        guid = str(uuid.uuid1())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:jon@example.com', 
            'name':'jon'},'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity17'},
            'context':{'registration': guid, 'instructor': {'objectType':'Agent','name':'jon',
            'mbox':'mailto:jon@example.com'},'contextActivities': {'other': {'id': 'act:NewActivityID'}},
            'revision': 'foo', 'platform':'bar','language': 'en-US', 'statement': {'id': stmt_guid,
            'objectType':'StatementRef'}}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        conactor = models.agent.objects.get(id=stmt.model_object.context.instructor.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.statement.objects.get(statement_id=stmt_ref.ref_id)
        context_activities = stmt.model_object.context.contextactivity_set.all()

        st = models.statement.objects.get(id=stmt.model_object.id)

        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)
        self.assertEqual(st.context.instructor.id, conactor.id)

        self.assertEqual(context.registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].get_context_activities()[0].activity_id, 'act:NewActivityID')
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')
        
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")
        
        self.assertEqual(conactor.objectType, 'Agent')
        
        self.assertEqual(conactor.name, 'jon')
        self.assertEqual(conactor.mbox, 'mailto:jon@example.com') 


    def test_actor_with_context_stmt(self):
        stmt_guid = str(uuid.uuid1())
        existing_stmt = Statement.Statement(json.dumps({'statement_id':stmt_guid, 'actor':{'objectType':'Agent',
            'mbox':'mailto:s@s.com'},'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}}))

        guid = str(uuid.uuid1())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent', 'name': 'steve',
            'mbox':'mailto:mailto:s@s.com'},'verb': {"id":"verb:verb/url"},"object": {'id':'act:activity18'},
            'context':{'registration': guid, 'instructor': {'objectType':'Agent','name':'jon',
            'mbox':'mailto:jon@example.com'},'contextActivities': {'other': {'id': 'act:NewActivityID1'}},
            'revision': 'foob', 'platform':'bard','language': 'en-US', 'statement': {'id':stmt_guid,
            "objectType":"StatementRef"}}}))

        activity = models.activity.objects.get(id=stmt.model_object.stmt_object.id)
        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        instructor = models.agent.objects.get(id=stmt.model_object.context.instructor.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.statement.objects.get(statement_id=stmt_ref.ref_id)
        st = models.statement.objects.get(id=stmt.model_object.id)
        context_activities = stmt.model_object.context.contextactivity_set.all()

        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)
        self.assertEqual(st.context.instructor.id, instructor.id)
        self.assertEqual(st.verb.verb_id, "verb:verb/url" )

        self.assertEqual(context.registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].get_context_activities()[0].activity_id, 'act:NewActivityID1')
        self.assertEqual(context.revision, 'foob')
        self.assertEqual(context.platform, 'bard')
        self.assertEqual(context.language, 'en-US')
        
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")
        
        self.assertEqual(instructor.objectType, 'Agent')
        
        self.assertEqual(instructor.name, 'jon')
        self.assertEqual(instructor.mbox, 'mailto:jon@example.com') 


    def test_agent_as_object_with_context_stmt(self):
        stmt_guid = str(uuid.uuid1())
        existing_stmt = Statement.Statement(json.dumps({'statement_id':stmt_guid, 'actor':{'objectType':'Agent',
            'mbox':'mailto:mailto:s@s.com'},'verb': {"id":"verb:verb/url/outer"},"object": {'id':'act:activityy16'}}))

        guid = str(uuid.uuid1())
        stmt = Statement.Statement(
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

        ctxid = get_ctx_id(stmt.model_object)
        context = models.context.objects.get(id=ctxid)
        instructor = models.agent.objects.get(id=stmt.model_object.context.instructor.id)
        stmt_ref = models.StatementRef(ref_id=stmt_guid)
        neststmt = models.statement.objects.get(statement_id=stmt_ref.ref_id)
        context_activities = stmt.model_object.context.contextactivity_set.all()

        st = models.statement.objects.get(id=stmt.model_object.id)

        self.assertEqual(st.context.id, context.id)
        self.assertEqual(st.context.instructor.id, instructor.id)
        self.assertEqual(st.verb.verb_id, "verb:verb/url")

        self.assertEqual(context.registration, guid)
        self.assertEqual(context_activities[0].key, 'other')
        self.assertEqual(context_activities[0].get_context_activities()[0].activity_id, 'act:NewActivityID1')
        self.assertEqual(context.language, 'en-US')
        
        self.assertEqual(neststmt.verb.verb_id, "verb:verb/url/outer")
        
        self.assertEqual(instructor.objectType, 'Agent')
        
        # Should be jon
        self.assertEqual(instructor.name, 'jon')
        self.assertEqual(instructor.mbox, 'mailto:jon@example.com') 


    def test_agent_as_object(self):
        guid = str(uuid.uuid1())
        stmt = Statement.Statement(json.dumps({'object':{'objectType':'Agent', 'name': 'lulu', 'openid':'luluid'}, 
            'verb': {"id":"verb:verb/url"},'actor':{'objectType':'Agent','mbox':'mailto:t@t.com'}}))

        st = models.statement.objects.get(id=stmt.model_object.id)
        agent = models.agent.objects.get(id=stmt.model_object.stmt_object.id)

        self.assertEqual(agent.name, 'lulu')
        self.assertEqual(agent.openid, 'luluid')


    def test_unallowed_substmt_field(self):
        stmt = {'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
            'verb': {"id":"verb:verb/url"}, 'object':{'objectType':'SubStatement',
            'actor':{'objectType':'Agent','mbox':'mailto:ss@ss.com'},'verb': {"id":"verb:verb/url/nest"},
            'object': {'objectType':'activity', 'id':'act:testex.com'},
            'authority':{'objectType':'Agent','mbox':'mailto:s@s.com'}}}
        self.assertRaises(ParamError, Statement.Statement, json.dumps(stmt))


    def test_nested_substatement(self):
        stmt = {'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
            'verb': {"id":"verb:verb/url"}, 'object':{'objectType':'SubStatement',
            'actor':{'objectType':'Agent','mbox':'mailto:ss@ss.com'},'verb': {"id":"verb:verb/url/nest"},
            'object': {'objectType':'SubStatement', 'actor':{'objectType':'Agent','mbox':'mailto:sss@sss.com'},
            'verb':{'id':'verb:verb/url/nest/nest'}, 'object':{'id':'act://activity/url'}}}}
        self.assertRaises(ParamError, Statement.Statement, json.dumps(stmt))


    def test_substatement_as_object(self):
        guid = str(uuid.uuid1())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent','mbox':'mailto:s@s.com'},
            'verb': {"id":"verb:verb/url"}, 'object':{'objectType':'SubStatement',
            'actor':{'objectType':'Agent','mbox':'mailto:ss@ss.com'},'verb': {"id":"verb:verb/url/nest"},
            'object': {'objectType':'activity', 'id':'act:testex.com'}, 'result':{'completion': True, 'success': True,
            'response': 'kicked'}, 'context':{'registration': guid,
            'contextActivities': {'other': {'id': 'act:NewActivityID'}},'revision': 'foo', 'platform':'bar',
            'language': 'en-US', 'extensions':{'ext:k1': 'v1', 'ext:k2': 'v2'}}}}))

        outer_stmt = models.statement.objects.get(id=stmt.model_object.id)
        sub_stmt = models.SubStatement.objects.get(id=outer_stmt.stmt_object.id)
        sub_obj = models.activity.objects.get(id=sub_stmt.stmt_object.id)
        sub_act = models.agent.objects.get(id=sub_stmt.actor.id)
        sub_con = models.context.objects.get(id=sub_stmt.context.id)
        self.assertEqual(len(sub_stmt.result.all()), 1)
        resid = sub_stmt.result.all()[0].id
        sub_res = models.result.objects.get(id=resid)

        self.assertEqual(outer_stmt.verb.verb_id, "verb:verb/url")
        self.assertEqual(outer_stmt.actor.mbox, 'mailto:s@s.com')        
        self.assertEqual(sub_stmt.verb.verb_id, "verb:verb/url/nest")
        self.assertEqual(sub_obj.activity_id, 'act:testex.com')
        self.assertEqual(sub_act.mbox, 'mailto:ss@ss.com')
        self.assertEqual(sub_con.registration, guid)
        self.assertEqual(sub_res.response, 'kicked')
        

    def test_model_authoritative_set(self):
        stmt = Statement.Statement(json.dumps({"actor":{"name":"tom","mbox":"mailto:tom@example.com"},
            'verb': {"id":"verb:verb/url"}, "object": {"id":"act:activity"}}))
        self.assertTrue(models.statement.objects.get(pk=stmt.model_object.pk).authoritative)
        
        stmt2 = Statement.Statement(json.dumps({"actor":{"name":"tom","mbox":"mailto:tom@example.com"},
            'verb': {"id":"verb:verb/url"}, "object": {"id":"act:activity"}}))
        self.assertTrue(models.statement.objects.get(pk=stmt2.model_object.pk).authoritative)
        self.assertFalse(models.statement.objects.get(pk=stmt.model_object.pk).authoritative)
        
        stmt3 = Statement.Statement(json.dumps({"actor":{"name":"tom","mbox":"mailto:tom@example.com"},
            'verb': {"id":"verb:verb/url"}, "object": {"id":"act:activity2"}}))

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
        
        stmt = Statement.Statement(json.dumps({"actor":testagent, 'verb': {"id":"verb:verb/url"},"object": {"id":"act:activity5",
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

    # Verbs cannot share languagemaps. Will have many lang_maps attached to one verb
    def test_verb_delete(self):
        verb1 = models.Verb.objects.create(verb_id="verb:created")
        lang_map1 = models.LanguageMap.objects.create(key='en-US', value='created', content_object=verb1)
        lang_map2 = models.LanguageMap.objects.create(key='en-GB', value='created', content_object=verb1)

        # Should remove any lang maps attached to it
        models.Verb.objects.get(id=verb1.id).delete()
        verbs = len(models.Verb.objects.all())
        lang_maps = len(models.LanguageMap.objects.all())
        self.assertEqual(verbs, 0)
        self.assertEqual(lang_maps, 0)

        verb2 = models.Verb.objects.create(verb_id="verb:deleted")
        lang_map3 = models.LanguageMap.objects.create(key='en-US', value='deleted', content_object=verb2)
        lang_map4 = models.LanguageMap.objects.create(key='en-GB', value='deleted', content_object=verb2)

        # Deleting lang map should not affect anything else
        models.LanguageMap.objects.get(id=lang_map3.id).delete()
        verbs = len(models.Verb.objects.all())
        lang_maps = len(models.LanguageMap.objects.all())
        self.assertEqual(verbs, 1)
        self.assertEqual(lang_maps, 1)

    def test_result_delete(self):
        stmt1 = Statement.Statement(json.dumps(
            {'actor':{'mbox':'mailto:s@s.com'},
            'verb':{'id':'verb:test', 'display':{'en-US':'test'}},
            'object':{'id':'act:test_act'}}))

        result1 = models.result.objects.create(success=True, content_object=stmt1.model_object)
        score1 = models.score.objects.create(scaled=0.50, result=result1)
        res_ext1 = models.extensions.objects.create(key='key1', value='value1', content_object=result1)
        res_ext2 = models.extensions.objects.create(key='key2', value='value2', content_object=result1)

        # There should never be a time that a result object gets deleted by itself. In this case, the statement
        # will remain
        models.result.objects.get(id=result1.id).delete()
        stmts = len(models.statement.objects.all())
        results = len(models.result.objects.all())
        scores = len(models.score.objects.all())
        res_exts = len(models.extensions.objects.all())
        self.assertEqual(stmts, 1)
        self.assertEqual(results, 0)
        self.assertEqual(scores, 0)
        self.assertEqual(res_exts, 0)

        stmt2 = Statement.Statement(json.dumps(
            {'actor':{'mbox':'mailto:s@s.com'},
            'verb':{'id':'verb:test', 'display':{'en-US':'test'}},
            'object':{'id':'act:test_act'}}))

        result2 = models.result.objects.create(success=True, content_object=stmt2.model_object)
        score2 = models.score.objects.create(scaled=0.50, result=result2)
        res_ext3 = models.extensions.objects.create(key='key3', value='value4', content_object=result2)
        res_ext4 = models.extensions.objects.create(key='key3', value='value4', content_object=result2)

        # There should never be a time that a score object gets deleted by itself. It is OneToOne with result,
        # the result object does not get removed. Once again stmt will remain
        models.score.objects.get(id=score2.id).delete()
        stmts = len(models.statement.objects.all())
        results = len(models.result.objects.all())
        scores = len(models.score.objects.all())
        res_exts = len(models.extensions.objects.all())
        # Previous stmt and this one
        self.assertEqual(stmts, 2)
        self.assertEqual(results, 1)
        self.assertEqual(scores, 0)
        self.assertEqual(res_exts, 2)

        stmt3 = Statement.Statement(json.dumps(
            {'actor':{'mbox':'mailto:s@s.com'},
            'verb':{'id':'verb:test', 'display':{'en-US':'test'}},
            'object':{'id':'act:test_act'}}))

        result3 = models.result.objects.create(success=True, content_object=stmt3.model_object)
        score3 = models.score.objects.create(scaled=0.50, result=result3)
        res_ext5 = models.extensions.objects.create(key='key3', value='value4', content_object=result3)
        res_ext6 = models.extensions.objects.create(key='key3', value='value4', content_object=result3)

        # Deleting an ext should not affect anything else
        models.extensions.objects.get(id=res_ext6.id).delete()
        stmts = len(models.statement.objects.all())
        results = len(models.result.objects.all())
        scores = len(models.score.objects.all())
        res_exts = len(models.extensions.objects.all())
        # Will be two results, one from before and this one
        self.assertEqual(results, 2)
        self.assertEqual(scores, 1)
        # Will be three exts, two from before and this one
        self.assertEqual(res_exts, 3)
        # 2 stmts from before and this one
        self.assertEqual(stmts, 3)

    def test_activity_definition_delete(self):
        act1 = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'act:foo',
                'definition': {'name': {'en-UK':'name', 'en-US':'nombre'},'description': {'en-UK':'desc',
                'en-US': 'tdesc'},'type': 'course','interactionType': 'intType2',
                'extensions': {'ext:key1': 'value1','ext:key2': 'value2','ext:key3': 'value3'}}}))

        act2 = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'act:baz',
                'definition': {'name': {'en-UK':'name2', 'en-US':'nombre2'},'description': {'en-UK':'desc2',
                'en-US': 'tdesc2'},'type': 'course','interactionType': 'intType2',
                'extensions': {'ext2:key1': 'value1','ext2:key2': 'value2','ext2:key3': 'value3'}}}))

        # Set each one individually, if try to get in list, not always in same order
        act_def1 = models.activity_definition.objects.get(activity=act1.activity)
        act_def2 = models.activity_definition.objects.get(activity=act2.activity)
        
        name_lang1_1 = models.name_lang.objects.get(value='name')
        name_lang1_2 = models.name_lang.objects.get(value='nombre')
        name_lang2_1= models.name_lang.objects.get(value='name2')
        name_lang2_2= models.name_lang.objects.get(value='nombre2')
        
        desc_lang1_1 = models.desc_lang.objects.get(value='desc')
        desc_lang1_2 = models.desc_lang.objects.get(value='tdesc')
        desc_lang2_1 = models.desc_lang.objects.get(value='desc2')
        desc_lang2_2 = models.desc_lang.objects.get(value='tdesc2')
        
        ext1_1 = models.extensions.objects.get(key='ext:key1')
        ext1_2 = models.extensions.objects.get(key='ext:key2')
        ext1_3 = models.extensions.objects.get(key='ext:key3')
        ext2_1 = models.extensions.objects.get(key='ext2:key1')
        ext2_2 = models.extensions.objects.get(key='ext2:key2')
        ext2_3 = models.extensions.objects.get(key='ext2:key3')
        
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        self.assertEqual(name_langs, 4)
        self.assertEqual(desc_langs, 4)
        self.assertEqual(exts, 6)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)

        # Should only be three name_langs now
        models.name_lang.objects.get(id=name_lang1_1.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        self.assertEqual(name_langs, 3)
        self.assertEqual(desc_langs, 4)
        self.assertEqual(exts, 6)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)

        # Should only be three desc_langs now
        models.desc_lang.objects.get(id=desc_lang2_1.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        self.assertEqual(name_langs, 3)
        self.assertEqual(desc_langs, 3)
        self.assertEqual(exts, 6)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)

        # Should only be five extensions now
        models.extensions.objects.get(id=ext1_1.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        self.assertEqual(name_langs, 3)
        self.assertEqual(desc_langs, 3)
        self.assertEqual(exts, 5)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)

        # Delete second activity def(will never get deleted w/o activity being deleted)
        # Deletes both of it's name_langs, remaining desc_lang, all 3 of it's extensions
        models.activity_definition.objects.get(id=act_def2.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 2)
        self.assertEqual(exts, 2)
        self.assertEqual(act_defs, 1)
        self.assertEqual(acts, 2)

        # Activity 2 will still remain
        models.activity.objects.get(id=act1.activity.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        self.assertEqual(name_langs, 0)
        self.assertEqual(desc_langs, 0)
        self.assertEqual(exts, 0)
        self.assertEqual(act_defs, 0)
        self.assertEqual(acts, 1)

    def test_activity_correctresponsepattern(self):
        act1 = Activity.Activity(json.dumps({
            'objectType': 'Activity', 'id':'act:foo',
            'definition': {'name': {'en-US':'testname'},'description': {'en-US':'testdesc'}, 
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction',
                'interactionType': 'true-false','correctResponsesPattern': ['true'],
                'extensions': {'ext:key1': 'value1'}}}))

        act2 = Activity.Activity(json.dumps({
            'objectType': 'Activity', 'id':'act:baz',
            'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'}, 
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction',
                'interactionType': 'true-false','correctResponsesPattern': ['true'],
                'extensions': {'ext2:key1': 'value1'}}}))

        # Set each one individually, if try to get in list, not always in same order
        act_def1 = models.activity_definition.objects.get(activity=act1.activity)
        act_def2 = models.activity_definition.objects.get(activity=act2.activity)
        
        name_lang1 = models.name_lang.objects.get(value='testname')
        name_lang2 = models.name_lang.objects.get(value='testname2')
        
        desc_lang1 = models.desc_lang.objects.get(value='testdesc')
        desc_lang2 = models.desc_lang.objects.get(value='testdesc2')
        
        ext1 = models.extensions.objects.get(key='ext:key1')
        ext2 = models.extensions.objects.get(key='ext2:key1')

        crp1 = models.activity_def_correctresponsespattern.objects.get(activity_definition=act_def1)
        crp2 = models.activity_def_correctresponsespattern.objects.get(activity_definition=act_def2)

        crp_answer1 = models.correctresponsespattern_answer.objects.get(correctresponsespattern=crp1)
        crp_answer2 = models.correctresponsespattern_answer.objects.get(correctresponsespattern=crp2)        

        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        self.assertEqual(name_langs, 2)
        self.assertEqual(desc_langs, 2)
        self.assertEqual(exts, 2)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crps, 2)
        self.assertEqual(crp_answers, 2)

        # Should only be 1 name_langs now
        models.name_lang.objects.get(id=name_lang1.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 2)
        self.assertEqual(exts, 2)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crps, 2)
        self.assertEqual(crp_answers, 2)

        # Should only be 1 desc_langs now
        models.desc_lang.objects.get(id=desc_lang2.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 1)
        self.assertEqual(exts, 2)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crps, 2)
        self.assertEqual(crp_answers, 2)

        # Should only be 1 extensions now
        models.extensions.objects.get(id=ext1.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 1)
        self.assertEqual(exts, 1)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crps, 2)
        self.assertEqual(crp_answers, 2)

        # Delete second activity def(will never get deleted w/o activity being deleted)
        # Deletes its name_langs, its extensions, crp, and crp answers
        models.activity_definition.objects.get(id=act_def2.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        self.assertEqual(name_langs, 0)
        self.assertEqual(desc_langs, 1)
        self.assertEqual(exts, 0)
        self.assertEqual(act_defs, 1)
        self.assertEqual(acts, 2)
        self.assertEqual(crps, 1)
        self.assertEqual(crp_answers, 1)

        # Deletes its desc lang, def, crp, and crp answer
        models.activity.objects.get(id=act1.activity.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        self.assertEqual(name_langs, 0)
        self.assertEqual(desc_langs, 0)
        self.assertEqual(exts, 0)
        self.assertEqual(act_defs, 0)
        self.assertEqual(acts, 1)
        self.assertEqual(crps, 0)
        self.assertEqual(crp_answers, 0)

    # Would be same for steps, target/source, and scale
    def test_activity_definition_choices(self):
        act1 = Activity.Activity(json.dumps(
            {'objectType': 'Activity', 'id':'act:foo',
                'definition': {'name': {'en-US':'testname1'},'description': {'en-US':'testdesc1'},
                    'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction',
                    'interactionType': 'choice',
                    'correctResponsesPattern': ['golf', 'tetris'],'choices':[
                    {'id': 'golf', 'description': {'en-US':'Golf Example', 'en-GB': 'GOLF'}},
                    {'id': 'tetris','description':{'en-US': 'Tetris Example', 'en-GB': 'TETRIS'}},
                    {'id':'facebook', 'description':{'en-US':'Facebook App', 'en-GB': 'FACEBOOK'}},
                    {'id':'scrabble', 'description': {'en-US': 'Scrabble Example', 'en-GB': 'SCRABBLE'}}],
                    'extensions': {'ext1:key1': 'value1'}}}))

        act2 = Activity.Activity(json.dumps(
            {'objectType': 'Activity', 'id':'act:biz',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'},
                    'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction',
                    'interactionType': 'choice',
                    'correctResponsesPattern': ['golf', 'tetris'],'choices':[
                    {'id': 'golf', 'description': {'en-US':'Golf Example', 'en-GB': 'GOLF'}},
                    {'id': 'tetris','description':{'en-US': 'Tetris Example', 'en-GB': 'TETRIS'}},
                    {'id':'facebook', 'description':{'en-US':'Facebook App', 'en-GB': 'FACEBOOK'}},
                    {'id':'scrabble', 'description': {'en-US': 'Scrabble Example', 'en-GB': 'SCRABBLE'}}],
                    'extensions': {'ext2:key1': 'value1'}}}))

        # Set each one individually, if try to get in list, not always in same order
        act_def1 = models.activity_definition.objects.get(activity=act1.activity)
        act_def2 = models.activity_definition.objects.get(activity=act2.activity)
        
        name_lang1 = models.name_lang.objects.get(value='testname1')
        name_lang2 = models.name_lang.objects.get(value='testname2')
        
        desc_lang1 = models.desc_lang.objects.get(value='testdesc1')
        desc_lang2 = models.desc_lang.objects.get(value='testdesc2')
        
        ext1 = models.extensions.objects.get(key='ext1:key1')
        ext2 = models.extensions.objects.get(key='ext2:key1')

        crp1 = models.activity_def_correctresponsespattern.objects.get(activity_definition=act_def1)
        crp2 = models.activity_def_correctresponsespattern.objects.get(activity_definition=act_def2)

        crp_answers1 = models.correctresponsespattern_answer.objects.filter(correctresponsespattern=crp1)
        crp_answers2 = models.correctresponsespattern_answer.objects.filter(correctresponsespattern=crp2)        

        choices1 = models.activity_definition_choice.objects.filter(activity_definition=act_def1)
        choices2 = models.activity_definition_choice.objects.filter(activity_definition=act_def2)

        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        choices = len(models.activity_definition_choice.objects.all())
        choice_lang_maps = len(models.LanguageMap.objects.all())
        self.assertEqual(name_langs, 2)
        self.assertEqual(desc_langs, 2)
        self.assertEqual(exts, 2)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crps, 2)
        self.assertEqual(crp_answers, 4)
        self.assertEqual(choices, 8)
        self.assertEqual(choice_lang_maps, 16)

        # Should only be 1 name_langs now
        models.name_lang.objects.get(id=name_lang1.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        choices = len(models.activity_definition_choice.objects.all())
        choice_lang_maps = len(models.LanguageMap.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 2)
        self.assertEqual(exts, 2)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crps, 2)
        self.assertEqual(crp_answers, 4)
        self.assertEqual(choices, 8)
        self.assertEqual(choice_lang_maps, 16)

        # Should only be 1 desc_langs now
        models.desc_lang.objects.get(id=desc_lang2.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        choices = len(models.activity_definition_choice.objects.all())
        choice_lang_maps = len(models.LanguageMap.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 1)
        self.assertEqual(exts, 2)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crps, 2)
        self.assertEqual(crp_answers, 4)
        self.assertEqual(choices, 8)
        self.assertEqual(choice_lang_maps, 16)

        # Should only be 1 extensions now
        models.extensions.objects.get(id=ext1.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        choices = len(models.activity_definition_choice.objects.all())
        choice_lang_maps = len(models.LanguageMap.objects.all())
        self.assertEqual(name_langs, 1)
        self.assertEqual(desc_langs, 1)
        self.assertEqual(exts, 1)
        self.assertEqual(act_defs, 2)
        self.assertEqual(acts, 2)
        self.assertEqual(crps, 2)
        self.assertEqual(crp_answers, 4)
        self.assertEqual(choices, 8)
        self.assertEqual(choice_lang_maps, 16)

        # Delete second activity def(will never get deleted w/o activity being deleted)
        # Deletes its name_langs, its extensions, crp, crp answers, and choices
        models.activity_definition.objects.get(id=act_def2.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        choices = len(models.activity_definition_choice.objects.all())
        choice_lang_maps = len(models.LanguageMap.objects.all())
        self.assertEqual(name_langs, 0)
        self.assertEqual(desc_langs, 1)
        self.assertEqual(exts, 0)
        self.assertEqual(act_defs, 1)
        self.assertEqual(acts, 2)
        self.assertEqual(crps, 1)
        self.assertEqual(crp_answers, 2)
        self.assertEqual(choices, 4)
        self.assertEqual(choice_lang_maps, 8)

        # Delete activity - removes its desc lang, def, crp, crp answers and choices
        models.activity.objects.get(id=act1.activity.id).delete()
        name_langs = len(models.name_lang.objects.all())
        desc_langs = len(models.desc_lang.objects.all())
        exts = len(models.extensions.objects.all())
        act_defs = len(models.activity_definition.objects.all())
        acts = len(models.activity.objects.all())
        crps = len(models.activity_def_correctresponsespattern.objects.all())
        crp_answers = len(models.correctresponsespattern_answer.objects.all())
        choices = len(models.activity_definition_choice.objects.all())
        choice_lang_maps = len(models.LanguageMap.objects.all())
        self.assertEqual(name_langs, 0)
        self.assertEqual(desc_langs, 0)
        self.assertEqual(exts, 0)
        self.assertEqual(act_defs, 0)
        self.assertEqual(acts, 1)
        self.assertEqual(crps, 0)
        self.assertEqual(crp_answers, 0)
        self.assertEqual(choices, 0)
        self.assertEqual(choice_lang_maps, 0)

    # Tests if an act from context already exists in a different stmt, if an act from context is the object in the
    # same stmt, and if an act from context doesn't exist anywhere
    def test_context_statement_delete(self):
        guid = str(uuid.uuid1())
        stmt1 = Statement.Statement(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity'}}))
        
        st1_id = str(stmt1.model_object.statement_id)
        stmt2 = Statement.Statement(json.dumps({
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

        self.assertEqual(len(models.StatementRef.objects.all()), 1)
        self.assertEqual(len(models.statement.objects.all()), 2)
        self.assertEqual(len(models.context.objects.all()), 1)
        self.assertEqual(len(models.agent.objects.all()), 2)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.activity.objects.all()), 3)

        models.statement.objects.get(id=stmt2.model_object.id).delete()
        self.assertEqual(len(models.StatementRef.objects.all()), 0)
        self.assertEqual(len(models.statement.objects.all()), 1)
        self.assertEqual(len(models.context.objects.all()), 0)
        self.assertEqual(len(models.agent.objects.all()), 1)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.activity.objects.all()), 1)
        self.assertIn('act:activity', models.activity.objects.values_list('activity_id', flat=True))

    def test_context_in_another_context_statement_delete(self):
        stmt1 = Statement.Statement(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url1"},
            "object": {'id':'act:activity1'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'team':{'objectType': 'Group', 'name':'mygroup',
                    'member':[{"name":"agent_in_group","mbox":"mailto:agentingroup@example.com"}]},
                'contextActivities': {'other': [{'id': 'act:activity1'},{'id':'act:activity2'}],
                'grouping':{'id':'act:activity3'}},'revision': 'foo', 'platform':'bar','language': 'en-US',
                'extensions':{'ext:key1': 'value1'}}}))
        
        stmt2 = Statement.Statement(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url2"},
            "object": {'id':'act:activity4'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:inst@inst.com'},
                'team':{'objectType': 'Group', 'name':'mygroup',
                    'member':[{"name":"agent_in_group","mbox":"mailto:agentingroup@example.com"}]},
                'contextActivities': {'other': [{'id': 'act:activity2'},{'id':'act:activity3'}],
                'grouping':{'id':'act:activity5'}},'revision': 'foo', 'platform':'bar','language': 'en-US'}}))

        stmt3 = Statement.Statement(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url3"},
            "object": {'id':'act:activity1'},
            'context':{'instructor':{'objectType':'Agent', 'mbox':'mailto:three@inst.com'},
                'team':{'objectType': 'Group', 'name':'mygroup',
                    'member':[{"name":"agent_in_group","mbox":"mailto:agentingroup@example.com"}]},
                'contextActivities': {'other': [{'id': 'act:activity6'},{'id':'act:activity5'}],
                'grouping':{'id':'act:activity2'}},'revision': 'three', 'platform':'bar','language': 'en-US'}}))

        self.assertEqual(len(models.activity.objects.all()), 6)
        # pdb.set_trace()
        models.statement.objects.get(id=stmt3.model_object.id).delete()
        self.assertEqual(len(models.activity.objects.all()), 5)
        activity_id_list = models.activity.objects.all().values_list('activity_id', flat=True)
        self.assertIn('act:activity1', activity_id_list)
        self.assertIn('act:activity2', activity_id_list)
        self.assertIn('act:activity3', activity_id_list)
        self.assertIn('act:activity4', activity_id_list)
        self.assertIn('act:activity5', activity_id_list)

        models.statement.objects.get(id=stmt2.model_object.id).delete()
        self.assertEqual(len(models.activity.objects.all()), 3)
        activity_id_list = models.activity.objects.all().values_list('activity_id', flat=True)
        self.assertIn('act:activity1', activity_id_list)
        self.assertIn('act:activity2', activity_id_list)
        self.assertIn('act:activity3', activity_id_list)

        models.statement.objects.get(id=stmt1.model_object.id).delete()
        self.assertEqual(len(models.activity.objects.all()), 0)

    def test_simple_statement_delete(self):
        stmt1 = Statement.Statement(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:a@a.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'}}))
        
        stmt2 = Statement.Statement(json.dumps({
            'actor':{'objectType':'Agent','mbox':'mailto:b@b.com'},
            'verb': {"id":"verb:verb/url"},
            "object": {'id':'act:activity1'}}))

        self.assertEqual(len(models.agent.objects.all()), 2)
        self.assertEqual(len(models.activity.objects.all()), 1)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.statement.objects.all()), 2)

        models.statement.objects.get(id=stmt2.model_object.id).delete()

        self.assertEqual(len(models.agent.objects.all()), 1)
        self.assertEqual(models.agent.objects.all()[0].mbox, 'mailto:a@a.com')
        self.assertEqual(len(models.activity.objects.all()), 1)
        self.assertEqual(len(models.Verb.objects.all()), 1)
        self.assertEqual(len(models.statement.objects.all()), 1)
        self.assertEqual(models.statement.objects.all()[0].id, stmt1.model_object.id)

