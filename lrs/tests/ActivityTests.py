from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import views, models
from os import path
import sys
import json

_DIR = path.abspath(path.dirname(__file__))
sys.path.append(path.abspath(path.join(_DIR,"../objects")))
from lrs.objects import Activity

class ActivityTests(TestCase):
    
    def test_get(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity', 'id':'foobar'}))
        response = self.client.get(reverse(views.activities), {'activityId':'foobar'})
        self.assertEqual(response.content, '{"activity_id": "foobar", "objectType": "Activity"}')
        
    def test_get_def(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar1',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'course',
                'interactionType': 'intType'}})) 
        response = self.client.get(reverse(views.activities), {'activityId':'foobar1'})
        self.assertEqual(response.content, '{"definition": {"interactionType": "intType", "type": "course", "name": "testname", "description": "testdesc"}, "activity_id": "foobar1", "objectType": "Activity"}')

    def test_get_ext(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar2',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'course',
                'interactionType': 'intType2', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))
        response = self.client.get(reverse(views.activities), {'activityId':'foobar2'})
        self.assertEqual(response.content, '{"definition": {"interactionType": "intType2", "type": "course", "name": "testname2", "description": "testdesc2"}, "activity_id": "foobar2", "extensions": {"key3": "value3", "key2": "value2", "key1": "value1"}, "objectType": "Activity"}')

    def test_get_crp_multiple_choice(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar3',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'multiple-choice','correctResponsesPattern': ['golf', 'tetris'],'choices':
                [{'id': 'golf', 'description': {'en-US':'Golf Example'}},{'id': 'tetris',
                'description':{'en-US': 'Tetris Example'}}, {'id':'facebook', 'description':{'en-US':'Facebook App'}},
                {'id':'scrabble', 'description': {'en-US': 'Scrabble Example'}}]}}))        
        response = self.client.get(reverse(views.activities), {'activityId':'foobar3'})
        self.assertEqual(response.content, '{"choices": [{"id": "golf", "description": "{\\"en-US\\": \\"Golf Example\\"}"}, {"id": "tetris", "description": "{\\"en-US\\": \\"Tetris Example\\"}"}, {"id": "facebook", "description": "{\\"en-US\\": \\"Facebook App\\"}"}, {"id": "scrabble", "description": "{\\"en-US\\": \\"Scrabble Example\\"}"}], "definition": {"interactionType": "multiple-choice", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "foobar3", "correctResponsesPattern": ["golf", "tetris"], "objectType": "Activity"}')

    def test_get_crp_true_false(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar4',
        'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
        'interactionType': 'true-false','correctResponsesPattern': ['true']}}))
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar4'})
        self.assertEqual(response.content, '{"definition": {"interactionType": "true-false", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "foobar4", "correctResponsesPattern": ["true"], "objectType": "Activity"}')

    def test_get_crp_fill_in(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar5',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'fill-in','correctResponsesPattern': ['Fill in answer']}}))
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar5'})       
        self.assertEqual(response.content, '{"definition": {"interactionType": "fill-in", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "foobar5", "correctResponsesPattern": ["Fill in answer"], "objectType": "Activity"}')

    def test_get_crp_long_fill_in(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar6',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'fill-in','correctResponsesPattern': ['Long fill in answer']}}))        
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar6'})       
        self.assertEqual(response.content, '{"definition": {"interactionType": "fill-in", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "foobar6", "correctResponsesPattern": ["Long fill in answer"], "objectType": "Activity"}')

    def test_get_crp_likert(self):
        act = Activity.Activity(json.dumps({'objectType': 'Still gonna be activity', 'id':'foobar7',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'likert','correctResponsesPattern': ['likert_3'],
                'scale':[{'id': 'likert_0', 'description': {'en-US':'Its OK'}},{'id': 'likert_1',
                'description':{'en-US': 'Its Pretty Cool'}}, {'id':'likert_2', 'description':{'en-US':'Its Damn Cool'}},
                {'id':'likert_3', 'description': {'en-US': 'Its Gonna Change the World'}}]}}))
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar7'})       
        self.assertEqual(response.content, '{"definition": {"interactionType": "likert", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "foobar7", "correctResponsesPattern": ["likert_3"], "scale": [{"id": "likert_0", "description": "{\\"en-US\\": \\"Its OK\\"}"}, {"id": "likert_1", "description": "{\\"en-US\\": \\"Its Pretty Cool\\"}"}, {"id": "likert_2", "description": "{\\"en-US\\": \\"Its Damn Cool\\"}"}, {"id": "likert_3", "description": "{\\"en-US\\": \\"Its Gonna Change the World\\"}"}], "objectType": "Activity"}')

    def test_get_crp_matching(self):
        act = Activity.Activity(json.dumps({'objectType': 'Still gonna be activity', 'id':'foobar8',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'matching','correctResponsesPattern': ['lou.3,tom.2,andy.1'],
                'source':[{'id': 'lou', 'description': {'en-US':'Lou'}},{'id': 'tom',
                'description':{'en-US': 'Tom'}}, {'id':'andy', 'description':{'en-US':'Andy'}}],
                'target':[{'id':'1', 'description':{'en-US': 'SCORM Engine'}},{'id':'2',
                'description':{'en-US': 'Pure-sewage'}},{'id':'3', 'description':{'en-US': 'SCORM Cloud'}}]}}))        
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar8'})       
        self.assertEqual(response.content, '{"definition": {"interactionType": "matching", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "foobar8", "target": [{"id": "1", "description": "{\\"en-US\\": \\"SCORM Engine\\"}"}, {"id": "2", "description": "{\\"en-US\\": \\"Pure-sewage\\"}"}, {"id": "3", "description": "{\\"en-US\\": \\"SCORM Cloud\\"}"}], "source": [{"id": "lou", "description": "{\\"en-US\\": \\"Lou\\"}"}, {"id": "tom", "description": "{\\"en-US\\": \\"Tom\\"}"}, {"id": "andy", "description": "{\\"en-US\\": \\"Andy\\"}"}], "correctResponsesPattern": ["lou.3,tom.2,andy.1"], "objectType": "Activity"}')

    def test_get_crp_performance(self):
        act = Activity.Activity(json.dumps({'objectType': 'activity', 'id':'foobar9',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'performance','correctResponsesPattern': ['pong.1,dg.10,lunch.4'],
                'steps':[{'id': 'pong', 'description': {'en-US':'Net pong matches won'}},{'id': 'dg',
                'description':{'en-US': 'Strokes over par in disc golf at Liberty'}},
                {'id':'lunch', 'description':{'en-US':'Lunch having been eaten'}}]}}))
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar9'})       
        self.assertEqual(response.content, '{"definition": {"interactionType": "performance", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "foobar9", "correctResponsesPattern": ["pong.1,dg.10,lunch.4"], "steps": [{"id": "pong", "description": "{\\"en-US\\": \\"Net pong matches won\\"}"}, {"id": "dg", "description": "{\\"en-US\\": \\"Strokes over par in disc golf at Liberty\\"}"}, {"id": "lunch", "description": "{\\"en-US\\": \\"Lunch having been eaten\\"}"}], "objectType": "Activity"}')

    def test_get_crp_sequencing(self):
        act = Activity.Activity(json.dumps({'objectType': 'activity', 'id':'foobar10',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'sequencing','correctResponsesPattern': ['lou,tom,andy,aaron'],
                'choices':[{'id': 'lou', 'description': {'en-US':'Lou'}},{'id': 'tom','description':{'en-US': 'Tom'}},
                {'id':'andy', 'description':{'en-US':'Andy'}},{'id':'aaron', 'description':{'en-US':'Aaron'}}]}}))        
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar10'})       
        self.assertEqual(response.content, '{"choices": [{"id": "lou", "description": "{\\"en-US\\": \\"Lou\\"}"}, {"id": "tom", "description": "{\\"en-US\\": \\"Tom\\"}"}, {"id": "andy", "description": "{\\"en-US\\": \\"Andy\\"}"}, {"id": "aaron", "description": "{\\"en-US\\": \\"Aaron\\"}"}], "definition": {"interactionType": "sequencing", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "foobar10", "correctResponsesPattern": ["lou,tom,andy,aaron"], "objectType": "Activity"}')

    def test_get_crp_numeric(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar11',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'numeric','correctResponsesPattern': ['4'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))        
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar11'})       
        self.assertEqual(response.content, '{"definition": {"interactionType": "numeric", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "foobar11", "correctResponsesPattern": ["4"], "extensions": {"key3": "value3", "key2": "value2", "key1": "value1"}, "objectType": "Activity"}')

    def test_get_crp_other(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id': 'foobar12',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'other','correctResponsesPattern': ['(35.937432,-86.868896)']}}))        
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar12'})       
        self.assertEqual(response.content, '{"definition": {"interactionType": "other", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "foobar12", "correctResponsesPattern": ["(35.937432,-86.868896)"], "objectType": "Activity"}')



    def test_get_no_activity(self):
        response = self.client.get(reverse(views.activities))
        self.assertContains(response, 'Error')
    
    def test_post(self):
        response = self.client.post(reverse(views.activities), {'activityId':'my_activity'},content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 405)

    def test_delete(self):
        response = self.client.delete(reverse(views.activities), {'activityId':'my_activity'},content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 405)

    def test_put(self):
        response = self.client.put(reverse(views.activities), {'activityId':'my_activity'},content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 405)

