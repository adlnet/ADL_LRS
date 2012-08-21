from django.test import TestCase
from django.test.utils import setup_test_environment
from lrs import models
import json
from django.core.exceptions import ValidationError
import urllib
from os import path
import sys

from lrs.objects import Activity, Statement, Actor

class StatementModelsTests(TestCase):
     
    def test_minimum_stmt(self):
        stmt = Statement.Statement(json.dumps({"verb":"created","object": {"id":"activity"}}))
        act = models.activity.objects.get(id=stmt.statement.stmt_object.id)

        self.assertEqual(stmt.statement.verb, 'created')
        self.assertEqual(stmt.statement.stmt_object.id, act.id)

        st = models.statement.objects.get(verb='created')
        self.assertEqual(st.stmt_object.id, act.id)

    def test_minimum_stmt_activity_object(self):
        stmt = Statement.Statement(json.dumps({"verb":"created","object": {"id":"activity1", "objectType": "Activity"}}))
        act = models.activity.objects.get(id=stmt.statement.stmt_object.id)
        
        self.assertEqual(stmt.statement.verb, 'created')
        self.assertEqual(stmt.statement.stmt_object.id, act.id)

        st = models.statement.objects.get(verb='created')
        self.assertEqual(st.stmt_object.id, act.id)

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

    '''
    def test_contradictory_completion_results_stmt(self):
    	#stmt = Statement.Statement(json.dumps({"verb":"completed","object": {'id':'activity3'},"result": {"completion": False}}))
    	
    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"mastered","object": {'id':'activity4'},
    					 "result":{"completion": False}}))

    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"completed","object": {'id':'activity3'},
    					 "result":{"completion": False}}))

    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"passed","object": {'id':'activity5'},
    					 "result":{"completion": False}}))
    	
    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"failed","object": {'id':'activity3'},
    					 "result":{"completion": False}})) 
		
    def test_contradictory_success_results_stmt(self):
    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"mastered","object": {'id':'activity4'},
    					 "result":{"success": False}}))
    	
    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"passed","object": {'id':'activity3'},
    					 "result":{"success": False}}))
    	
    	self.assertRaises(Exception, Statement.Statement, json.dumps({"verb":"failed","object": {'id':'activity3'},
    					 "result":{"success": True}})) 
	'''



