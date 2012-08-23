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

_DIR = path.abspath(path.dirname(__file__))
sys.path.append(path.abspath(path.join(_DIR,"../objects")))
from lrs.objects import Activity, Statement, Actor

class StatementModelsTests(TestCase):
     
    def test_minimum_stmt(self):
        stmt = Statement.Statement(json.dumps({"verb":"created", "object": {"id":"activity"}}))
        act = models.activity.objects.get(id=stmt.statement.stmt_object.id)

        self.assertEqual(stmt.statement.verb, 'created')
        self.assertEqual(stmt.statement.stmt_object.id, act.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, act.id)

    def test_minimum_stmt_activity_object(self):
        stmt = Statement.Statement(json.dumps({"verb":"created","object": {"id":"activity1", "objectType": "Activity"}}))
        act = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        
        self.assertEqual(stmt.statement.verb, 'created')
        self.assertEqual(stmt.statement.stmt_object.id, act.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, act.id)

    def test_actor_stmt(self):
        stmt = Statement.Statement(json.dumps({"actor":{'objectType':'Person','name':['bob'],'mbox':['bob@example.com']}, "verb":"created","object": {"id":"activity5", "objectType": "Activity"}}))
        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        actor = models.person.objects.get(id=stmt.statement.actor.id)
        actorName = models.agent_name.objects.get(agent=stmt.statement.actor)
        actorMbox = models.agent_mbox.objects.get(agent=stmt.statement.actor)

        self.assertEqual(stmt.statement.verb, 'created')
        self.assertEqual(stmt.statement.stmt_object.id, activity.id)
        self.assertEqual(stmt.statement.actor.id, actor.id)

        st = models.statement.objects.get(id=stmt.statement.id)
        self.assertEqual(st.stmt_object.id, activity.id)
        self.assertEqual(st.actor.id, actor.id)

        self.assertEqual(actorName.name, 'bob')
        self.assertEqual(actorMbox.mbox, 'bob@example.com')

    def test_voided_stmt(self):
        stmt = Statement.Statement(json.dumps({"verb":"mentioned","object": {'id':'activity2'}}))
        stID = stmt.statement.statement_id
        stModel = models.statement.objects.get(statement_id=stID)

        self.assertEqual(stModel.voided, False)
        
        stmt2 = Statement.Statement(json.dumps({'verb': 'voided', 'object': {'objectType':'Statement', 'id': str(stID)}}))
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
        stmt = Statement.Statement(json.dumps({"verb":"kicked","object": {'id':'activity12'}, "result": {'completion': True, 'success': True, 'response': 'kicked', 'duration': time}}))

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
        stmt = Statement.Statement(json.dumps({"actor":{'objectType':'Person','name':['jon'],'mbox':['jon@example.com']},"verb":"attempted","object": {'id':'activity13'}, "result": {'completion': True, 'success': True, 'response': 'yes', 'duration': time,
                                            'extensions':{'key1': 'value1', 'key2':'value2'}}}))

        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        result = models.result.objects.get(id=stmt.statement.result.id)
        actor = models.person.objects.get(id=stmt.statement.actor.id)
        actorName = models.agent_name.objects.get(agent=stmt.statement.actor)
        actorMbox = models.agent_mbox.objects.get(agent=stmt.statement.actor)
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

        self.assertEqual(actorName.name, 'jon')
        self.assertEqual(actorMbox.mbox, 'jon@example.com')

        self.assertIn('key1', extKeys)
        self.assertIn('key2', extKeys)
        self.assertIn('value1', extVals)
        self.assertIn('value2', extVals)

    def test_result_score_stmt(self):
        time = str(datetime.now())
        stmt = Statement.Statement(json.dumps({"actor":{'objectType':'Person','name':['jon'],'mbox':['jon@example.com']},"verb":"passed","object": {'id':'activity14'}, 
            "result": {'score':{'scaled':.95}, 'completion': True, 'success': True, 'response': 'yes', 'duration': time,
            'extensions':{'key1': 'value1', 'key2':'value2'}}}))

        activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        result = models.result.objects.get(id=stmt.statement.result.id)
        score = models.score.objects.get(id=stmt.statement.result.score.id)
        actor = models.person.objects.get(id=stmt.statement.actor.id)
        actorName = models.agent_name.objects.get(agent=stmt.statement.actor)
        actorMbox = models.agent_mbox.objects.get(agent=stmt.statement.actor)
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

        self.assertEqual(actorName.name, 'jon')
        self.assertEqual(actorMbox.mbox, 'jon@example.com')

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
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'NewActivityID'}}, 'revision': 'foo', 'platform':'bar',
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
                'context':{'registration': guid, 'contextActivities': {'other': {'id': 'NewActivityID'}}, 'revision': 'foo', 'platform':'bar',
                'language': 'en-US', 'extensions':{'k1': 'v1', 'k2': 'v2'}}}))

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

    # def test_stmt_in_context_stmt(self):
    #     guid = str(uuid.uuid4())
    #     stmt = Statement.Statement(json.dumps({"verb":"kicked","object": {'id':'activity16'},
    #             'context':{'registration': guid, 'contextActivities': {'other': {'id': 'NewActivityID'}}, 'revision': 'foo', 'platform':'bar',
    #             'language': 'en-US', 'statement': 'blah'}}))

        # activity = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        # context = models.context.objects.get(id=stmt.statement.context.id)
        # neststmt = models.statement.objects.get(id=stmt.statement.context.statement)

        # st = models.statement.objects.get(id=stmt.statement.id)
        # self.assertEqual(st.stmt_object.id, activity.id)
        # self.assertEqual(st.context.id, context.id)
        # self.assertEqual(st.context.statement, neststmt.id)

        # self.assertEqual(context.registration, guid)
        # self.assertEqual(str(context.contextActivities), str({u'other': {u'id': u'NewActivityID'}}))
        # self.assertEqual(context.revision, 'foo')
        # self.assertEqual(context.platform, 'bar')
        # self.assertEqual(context.language, 'en-US')
        # self.assertEqual(neststmt.verb, 'attempted')
        # self.assertEqual(neststmt.stmt_object.id, 'nextActivity')
        # 