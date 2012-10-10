from django.test import TestCase
from django.test.utils import setup_test_environment
from lrs import models
import json
from django.core.exceptions import ValidationError
import urllib
from datetime import datetime
from os import path
import sys
import uuid
import pdb

from lrs.objects import Statement

class StatementModelsTests(TestCase):
         

    def test_minimum_stmt(self):
        

        stmt = Statement.Statement(json.dumps({"actor":{"objectType":"Agent","mbox": "tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))

        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        verb = models.Verb.objects.get(id=stmt.statement.verb.id)
        actor = models.agent.objects.get(id=stmt.statement.actor.id)

        self.assertEqual(activity.activity_id, "http://example.adlnet.gov/tincan/example/simplestatement")
        self.assertEqual(actor.mbox, "tincan@adlnet.gov")
        self.assertEqual(verb.verb_id, "http://adlnet.gov/expapi/verbs/created")

    def test_given_stmtID_stmt(self):
        

        stmt = Statement.Statement(json.dumps({"statement_id":"blahID",
            "actor":{"objectType":"Agent","mbox": "tincan@adlnet.gov"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/created","display": {"en-US":"created", "en-GB":"made"}},
            "object":{"id":"http://example.adlnet.gov/tincan/example/simplestatement"}}))
        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        verb = models.Verb.objects.get(id=stmt.statement.verb.id)
        actor = models.agent.objects.get(id=stmt.statement.actor.id)
        gb_lang = verb.display.all()[0]
        us_lang = verb.display.all()[1]

        self.assertEqual(gb_lang.key, 'en-GB')
        self.assertEqual(gb_lang.value, 'made')
        self.assertEqual(us_lang.key, 'en-US')
        self.assertEqual(us_lang.value, 'created')        

        self.assertEqual(activity.activity_id, "http://example.adlnet.gov/tincan/example/simplestatement")
        self.assertEqual(actor.mbox, "tincan@adlnet.gov")
        self.assertEqual(verb.verb_id, "http://adlnet.gov/expapi/verbs/created")
        
        st = models.statement.objects.get(statement_id="blahID")
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.verb.id, verb.id)


    def test_existing_stmtID_stmt(self):
        
        stmt = Statement.Statement(json.dumps({"statement_id":"blahID","verb":{"id":"verb/url",
            "display":{"en-US":"myverb"}}, "object": {"id":"activity"}, "actor":"objectType":"Agent",
            "mbox":"t@t.com"}))
        self.assertRaises(Exception, Statement.Statement, json.dumps({"object": {'id':'activity2'},
            "verb":{"id":"verb/url","display":{"en-US":"myverb"}},"statement_id":"blahID"}))

    def test_minimum_stmt_activity_object(self):


        stmt = Statement.Statement(json.dumps({"verb":"created","object": {"id":"activity1",
            "objectType": "Activity"}}))
        act = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        
        self.assertEqual(stmt.statement.verb, 'created')
        self.assertEqual(stmt.statement.stmt_object.id, act.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, act.id)

    def test_actor_stmt(self):
        stmt = Statement.Statement(json.dumps({"actor":{'objectType':'Agent','name':'bob','mbox':'bob@example.com'}, "verb":"created","object": {"id":"activity5", "objectType": "Activity"}}))
        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        actor = models.agent.objects.get(id=stmt.statement.actor.id)

        self.assertEqual(stmt.statement.verb, 'created')
        self.assertEqual(stmt.statement.stmt_object.id, activity.id)
        self.assertEqual(stmt.statement.actor.id, actor.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(actor.name, 'bob')
        self.assertEqual(actor.mbox, 'bob@example.com')

    def test_authority_stmt(self):
        stmt = Statement.Statement(json.dumps({"authority":{'objectType':'Agent','name':'bill','mbox':'bill@example.com'}, "verb":"created","object": {"id":"activity21", "objectType": "Activity"}}))
        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        authority = models.agent.objects.get(id=stmt.statement.authority.id)

        self.assertEqual(stmt.statement.verb, 'created')
        self.assertEqual(stmt.statement.stmt_object.id, activity.id)
        self.assertEqual(stmt.statement.authority.id, authority.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.authority.id, authority.id)

        self.assertEqual(authority.name, 'bill')
        self.assertEqual(authority.mbox, 'bill@example.com')
        

    def test_voided_stmt(self):


        stmt = Statement.Statement(json.dumps({"verb":"mentioned","object": {'id':'activity2'}}))
        stID = stmt.statement.statement_id
        stModel = models.statement.objects.get(statement_id=stID)

        self.assertEqual(stModel.voided, False)
        stmt2 = Statement.Statement(json.dumps({'verb': 'voided', 'object': {'objectType':'Statement',
            'id': str(stID)}}))
        stModel = models.statement.objects.get(statement_id=stID)        
        
        self.assertEqual(stModel.voided, True)

    def test_no_verb_stmt(self):


        self.assertRaises(Exception, Statement.Statement, json.dumps({"object": {'id':'activity2'}}))

    def test_no_object_stmt(self):
        

        self.assertRaises(Exception, Statement.Statement, json.dumps({"verb": "cheated"}))

    def test_not_json_stmt(self):
    	

        self.assertRaises(Exception, Statement.Statement, "This will fail.")

    def test_voided_true_stmt(self):
        self.assertRaises(Exception, Statement.Statement, json.dumps({'verb': 'kicked', 'voided': True, 'object': {'id':'activity3'}}))

        self.assertRaises(Exception, Statement.Statement, json.dumps({'verb': 'kicked', 'voided': True,
            'object': {'id':'activity3'}}))

    def test_contradictory_completion_result_stmt(self):


    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"mastered","object": {'id':'activity4'},
    					 "result":{"completion": False}}))

    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"completed","object": {'id':'activity5'},
    					 "result":{"completion": False}}))

    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"passed","object": {'id':'activity6'},
    					 "result":{"completion": False}}))
    	
    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"failed","object": {'id':'activity7'},
    					 "result":{"completion": False}})) 
		
    def test_contradictory_success_result_stmt(self):


    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"mastered","object": {'id':'activity8'},
    					 "result":{"success": False}}))
    	
    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"passed","object": {'id':'activity9'},
    					 "result":{"success": False}}))
    	
    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"failed","object": {'id':'activity10'},
    					 "result":{"success": True}})) 

    def test_string_result_stmt(self):
        stmt = Statement.Statement(json.dumps({"verb":"attempted","object": {"id":"activity11"}, "result": "This is a string."}))


        stmt = Statement.Statement(json.dumps({"verb":"attempted","object": {"id":"activity11"},
            "result": "This is a string."}))
        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        result = models.result.objects.get(id=stmt.statement.result.id)
        ext = models.result_extensions.objects.get(result=result)

        self.assertEqual(stmt.statement.verb, 'attempted')
        self.assertEqual(stmt.statement.stmt_object.id, activity.id)
        self.assertEqual(stmt.statement.result.id, result.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.result.id, result.id)

        self.assertEqual(ext.key, 'resultString')
        self.assertEqual(ext.value, 'This is a string.')


    def test_result_stmt(self):


        time = str(datetime.now())
        stmt = Statement.Statement(json.dumps({"verb":"kicked","object": {'id':'activity12'},
            "result": {'completion': True, 'success': True, 'response': 'kicked', 'duration': time}}))
        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        result = models.result.objects.get(id=stmt.statement.result.id)

        self.assertEqual(stmt.statement.verb, 'kicked')
        self.assertEqual(stmt.statement.stmt_object.id, activity.id)
        self.assertEqual(stmt.statement.result.id, result.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.result.id, result.id)

        self.assertEqual(result.completion, 'True')
        self.assertEqual(result.success, True)
        self.assertEqual(result.response, 'kicked')
        self.assertEqual(result.duration, time)

    def test_result_ext_stmt(self):


        time = str(datetime.now())
        stmt = Statement.Statement(json.dumps({"actor":{'objectType':'Person','name':'jon',
            'mbox':'jon@example.com'},"verb":"attempted","object": {'id':'activity13'}, 
            "result": {'completion': True, 'success': True, 'response': 'yes', 'duration': time,
            'extensions':{'key1': 'value1', 'key2':'value2'}}}))
        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        result = models.result.objects.get(id=stmt.statement.result.id)
        actor = models.agent.objects.get(id=stmt.statement.actor.id)
        extList = models.result_extensions.objects.values_list().filter(result=result)
        extKeys = [ext[1] for ext in extList]
        extVals = [ext[2] for ext in extList]

        self.assertEqual(stmt.statement.verb, 'attempted')
        self.assertEqual(stmt.statement.stmt_object.id, activity.id)
        self.assertEqual(stmt.statement.result.id, result.id)
        self.assertEqual(stmt.statement.actor.id, actor.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.result.id, result.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(result.completion, 'True')
        self.assertEqual(result.success, True)
        self.assertEqual(result.response, 'yes')
        self.assertEqual(result.duration, time)

        self.assertEqual(actor.name, 'jon')
        self.assertEqual(actor.mbox, 'jon@example.com')

        self.assertIn('key1', extKeys)
        self.assertIn('key2', extKeys)
        self.assertIn('value1', extVals)
        self.assertIn('value2', extVals)

    def test_result_score_stmt(self):


        time = str(datetime.now())
        stmt = Statement.Statement(json.dumps({"actor":{'objectType':'Agent','name':'jon','mbox':'jon@example.com'},"verb":"passed","object": {'id':'activity14'}, 
            "result": {'score':{'scaled':.95}, 'completion': True, 'success': True, 'response': 'yes', 'duration': time,
            'extensions':{'key1': 'value1', 'key2':'value2'}}}))

        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        result = models.result.objects.get(id=stmt.statement.result.id)
        score = models.score.objects.get(id=stmt.statement.result.score.id)
        actor = models.agent.objects.get(id=stmt.statement.actor.id)
        extList = models.result_extensions.objects.values_list().filter(result=result)
        extKeys = [ext[1] for ext in extList]
        extVals = [ext[2] for ext in extList]

        self.assertEqual(stmt.statement.verb, 'passed')
        self.assertEqual(stmt.statement.stmt_object.id, activity.id)
        self.assertEqual(stmt.statement.result.id, result.id)
        self.assertEqual(stmt.statement.actor.id, actor.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.result.id, result.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(result.completion, 'True')
        self.assertEqual(result.success, True)
        self.assertEqual(result.response, 'yes')
        self.assertEqual(result.duration, time)
        self.assertEqual(result.score.id, score.id)

        self.assertEqual(score.scaled, .95)

        self.assertEqual(activity.activity_id, 'activity14')

        self.assertEqual(actor.name, 'jon')
        self.assertEqual(actor.mbox, 'jon@example.com')

        self.assertIn('key1', extKeys)
        self.assertIn('key2', extKeys)
        self.assertIn('value1', extVals)
        self.assertIn('value2', extVals)

    def test_no_registration_context_stmt(self):


        self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"failed","object": {'id':'activity14'},
                         'context': {'contextActivities': {'foo':'bar'}}})) 

    def test_no_contextActivities_content_stmt(self):


        self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"failed","object": {'id':'activity14'},
                         'context': {'registration':'uuid'}})) 

    def test_context_stmt(self):


        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({"verb":"kicked","object": {'id':'activity15'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'NewActivityID'}},
                'revision': 'foo', 'platform':'bar',
                'language': 'en-US'}}))

        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        context = models.context.objects.get(id=stmt.statement.context.id)

        self.assertEqual(stmt.statement.verb, 'kicked')
        self.assertEqual(stmt.statement.stmt_object.id, activity.id)
        self.assertEqual(stmt.statement.context.id, context.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)

        self.assertEqual(context.registration, guid)
        self.assertEqual(str(context.contextActivities), str({u'other': {u'id': u'NewActivityID'}}))
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')

    def test_context_ext_stmt(self):


        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({"verb":"kicked","object": {'id':'activity16'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'NewActivityID'}},
                'revision': 'foo', 'platform':'bar','language': 'en-US', 'extensions':{'k1': 'v1', 'k2': 'v2'}}}))

        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        context = models.context.objects.get(id=stmt.statement.context.id)
        extList = models.context_extensions.objects.values_list().filter(context=context)
        extKeys = [ext[1] for ext in extList]
        extVals = [ext[2] for ext in extList]

        self.assertEqual(stmt.statement.verb, 'kicked')
        self.assertEqual(stmt.statement.stmt_object.id, activity.id)
        self.assertEqual(stmt.statement.context.id, context.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)

        self.assertEqual(context.registration, guid)
        self.assertEqual(str(context.contextActivities), str({u'other': {u'id': u'NewActivityID'}}))
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')

        self.assertIn('k1', extKeys)
        self.assertIn('k2', extKeys)
        self.assertIn('v1', extVals)
        self.assertIn('v2', extVals)

    def test_stmt_in_context_stmt(self):


        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({"verb":"kicked","object": {'id':'activity16'},
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'NewActivityID'}}, 'revision': 'foo', 'platform':'bar',
                'language': 'en-US', 'statement': {'verb': 'graded', 'object':{'id':'NestContextAct'}}}}))

        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        context = models.context.objects.get(id=stmt.statement.context.id)
        neststmt = models.statement.objects.get(id=stmt.statement.context.statement)
        nestact = models.activity.objects.get(id=neststmt.stmt_object.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)
        self.assertEqual(st.context.statement, neststmt.id)

        self.assertEqual(context.registration, guid)
        self.assertEqual(str(context.contextActivities), str({u'other': {u'id': u'NewActivityID'}}))
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')
        self.assertEqual(neststmt.verb, 'graded')
        self.assertEqual(nestact.activity_id, 'NestContextAct')

    def test_instructor_in_context_stmt(self):


        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({"verb":"kicked","object": {'id':'activity17'},
                'context':{'registration': guid, 'instructor': {'objectType':'Agent','name':'jon','mbox':'jon@example.com'},
                'contextActivities': {'other': {'id': 'NewActivityID'}}, 'revision': 'foo', 'platform':'bar',
                'language': 'en-US', 'statement': {'verb': 'graded', 'object':{'id':'NestContextAct1'}}}}))

        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        context = models.context.objects.get(id=stmt.statement.context.id)
        conactor = models.agent.objects.get(id=stmt.statement.context.instructor.id)
        neststmt = models.statement.objects.get(id=stmt.statement.context.statement)
        nestactivity = models.activity.objects.get(id=neststmt.stmt_object.id)

        st = models.statement.objects.get(id=stmt.statement.id)

        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)
        self.assertEqual(st.context.statement, neststmt.id)
        self.assertEqual(st.context.instructor.id, conactor.id)

        self.assertEqual(context.registration, guid)
        self.assertEqual(str(context.contextActivities), str({u'other': {u'id': u'NewActivityID'}}))
        self.assertEqual(context.revision, 'foo')
        self.assertEqual(context.platform, 'bar')
        self.assertEqual(context.language, 'en-US')
        
        self.assertEqual(neststmt.verb, 'graded')
        
        self.assertEqual(nestactivity.activity_id, 'NestContextAct1')
        
        self.assertEqual(conactor.objectType, 'Agent')
        
        self.assertEqual(conactor.name, 'jon')
        self.assertEqual(conactor.mbox, 'jon@example.com') 

    def test_actor_with_context_stmt(self):


        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({'actor':{'objectType':'Agent', 'name': 'steve', 'mbox':'s@s.com'}, "verb":"kicked","object": {'id':'activity18'},
                'context':{'registration': guid, 'instructor': {'objectType':'Agent','name':'jon','mbox':'jon@example.com'},
                'contextActivities': {'other': {'id': 'NewActivityID1'}}, 'revision': 'foob', 'platform':'bard',
                'language': 'en-US', 'statement': {'verb': 'graded', 'object':{'id':'NestContextAct2'}}}}))

        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        context = models.context.objects.get(id=stmt.statement.context.id)
        conactor = models.agent.objects.get(id=stmt.statement.context.instructor.id)
        neststmt = models.statement.objects.get(id=stmt.statement.context.statement)
        nestactivity = models.activity.objects.get(id=neststmt.stmt_object.id)

        st = models.statement.objects.get(id=stmt.statement.id)

        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.context.id, context.id)
        self.assertEqual(st.context.statement, neststmt.id)
        self.assertEqual(st.context.instructor.id, conactor.id)

        self.assertEqual(context.registration, guid)
        self.assertEqual(str(context.contextActivities), str({u'other': {u'id': u'NewActivityID1'}}))
        self.assertEqual(context.revision, 'foob')
        self.assertEqual(context.platform, 'bard')
        self.assertEqual(context.language, 'en-US')
        
        self.assertEqual(neststmt.verb, 'graded')
        
        self.assertEqual(nestactivity.activity_id, 'NestContextAct2')
        
        self.assertEqual(conactor.objectType, 'Agent')
        
        self.assertEqual(conactor.name, 'steve')
        self.assertEqual(conactor.mbox, 's@s.com') 

    def test_agent_as_object_with_context_stmt(self):
        guid = str(uuid.uuid4())
        stmt = Statement.Statement(
            json.dumps(
                {'object':{
                    'objectType':'Agent', 
                    'name': 'lou', 
                    'mbox':'l@l.com'
                 }, 
                 "verb":"kicked",
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
                        'verb': 'graded', 
                        'object':{'id':'NestContextAct2'}
                    }
                 }
                }
            )
        )

        context = models.context.objects.get(id=stmt.statement.context.id)
        conactor = models.agent.objects.get(id=stmt.statement.context.instructor.id)
        neststmt = models.statement.objects.get(id=stmt.statement.context.statement)
        nestactivity = models.activity.objects.get(id=neststmt.stmt_object.id)

        st = models.statement.objects.get(id=stmt.statement.id)

        self.assertEqual(st.context.id, context.id)
        self.assertEqual(st.context.statement, neststmt.id)
        self.assertEqual(st.context.instructor.id, conactor.id)

        self.assertEqual(context.registration, guid)
        self.assertEqual(str(context.contextActivities), str({u'other': {u'id': u'NewActivityID1'}}))
        self.assertEqual(context.language, 'en-US')
        
        self.assertEqual(neststmt.verb, 'graded')
        
        self.assertEqual(nestactivity.activity_id, 'NestContextAct2')
        
        self.assertEqual(conactor.objectType, 'Agent')
        
        # Should be lou b/c actor or object of statement overrides instructor
        self.assertEqual(conactor.name, 'lou')
        self.assertEqual(conactor.mbox, 'l@l.com') 

    def test_agent_as_object(self):


        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({'object':{'objectType':'Agent', 'name': 'lulu', 'openid':'luluid'}, 
            "verb":"kicked"}))

        st = models.statement.objects.get(id=stmt.statement.id)
        agent = models.agent.objects.get(id=stmt.statement.stmt_object.id)

        self.assertEqual(agent.name, 'lulu')
        self.assertEqual(agent.openid, 'luluid')

    def test_stmt_as_object(self):


        guid = str(uuid.uuid4())
        stmt = Statement.Statement(json.dumps({"verb":"kicked", 'object':{'objectType':'Statement', 'verb': 'punched',
            'object': {'objectType':'activity', 'id':'testex.com'} }}))

        outer_stmt = models.statement.objects.get(id=stmt.statement.id)
        inner_stmt = models.statement.objects.get(id=outer_stmt.stmt_object.id)
        inner_act = models.activity.objects.get(id=inner_stmt.stmt_object.id)

        self.assertEqual(outer_stmt.verb, 'kicked')
        self.assertEqual(inner_stmt.verb, 'punched')
        self.assertEqual(inner_act.activity_id, 'testex.com')

    # def test_group_as_object(self):
    #     guid = str(uuid.uuid4())
    #     stmt = Statement.Statement(json.dumps({"verb":"kicked", 'object':{'objectType':'Group', }}))

    #     outer_stmt = models.statement.objects.get(id=stmt.statement.id)
    #     inner_stmt = models.statement.objects.get(id=outer_stmt.stmt_object.id)
    #     inner_act = models.activity.objects.get(id=inner_stmt.stmt_object.id)

    #     self.assertEqual(outer_stmt.verb, 'kicked')
    #     self.assertEqual(inner_stmt.verb, 'punched')
    #     self.assertEqual(inner_act.activity_id, 'http://testex.com')
        


    def test_model_authoritative_set(self):
        stmt = Statement.Statement(json.dumps({"actor":{"name":"tom","mbox":"mailto:tom@example.com"},"verb":"created", "object": {"id":"activity"}}))
        self.assertTrue(models.statement.objects.get(pk=stmt.statement.pk).authoritative)
        
        stmt2 = Statement.Statement(json.dumps({"actor":{"name":"tom","mbox":"mailto:tom@example.com"},"verb":"shared", "object": {"id":"activity"}}))
        self.assertTrue(models.statement.objects.get(pk=stmt2.statement.pk).authoritative)
        self.assertFalse(models.statement.objects.get(pk=stmt.statement.pk).authoritative)
        
        stmt3 = Statement.Statement(json.dumps({"actor":{"name":"tom","mbox":"mailto:tom@example.com"},"verb":"shared", "object": {"id":"activity2"}}))
        self.assertTrue(models.statement.objects.get(pk=stmt3.statement.pk).authoritative)
        self.assertTrue(models.statement.objects.get(pk=stmt2.statement.pk).authoritative)
        self.assertFalse(models.statement.objects.get(pk=stmt.statement.pk).authoritative)

    def test_group_stmt(self):
        ot = "Group"
        name = "the group SMT"
        mbox = "mailto:the.groupSMT@example.com"
        members = [{"name":"agentA","mbox":"mailto:agentA@example.com"},
                    {"name":"agentB","mbox":"mailto:agentB@example.com"}]
        testagent = json.dumps({"objectType":ot, "name":name, "mbox":mbox,"member":members})
        
        stmt = Statement.Statement(json.dumps({"actor":testagent, "verb":"created","object": {"id":"activity5", "objectType": "Activity"}}))
        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        actor = models.agent.objects.get(id=stmt.statement.actor.id)

        self.assertEqual(stmt.statement.verb, 'created')
        self.assertEqual(stmt.statement.stmt_object.id, activity.id)
        self.assertEqual(stmt.statement.actor.id, actor.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(actor.name, name)
        self.assertEqual(actor.mbox, mbox)
