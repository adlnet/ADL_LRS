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
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'/var/www/adllrs/activity/example.xml',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'course',
                'interactionType': 'intType'}})) 
     
        response = self.client.get(reverse(views.activities), {'activityId':'/var/www/adllrs/activity/example.xml'})
        self.assertEqual(response.content, '{"definition": {"interactionType": "intType", "type": "course", "name": "testname", "description": "testdesc"}, "activity_id": "/var/www/adllrs/activity/example.xml", "objectType": "Activity"}')

    def test_get_ext(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'food',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'course',
                'interactionType': 'intType2', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))
        response = self.client.get(reverse(views.activities), {'activityId':'food'})
        self.assertEqual(response.content, '{"definition": {"interactionType": "intType2", "type": "course", "name": "testname2", "description": "testdesc2"}, "activity_id": "food", "extensions": {"key3": "value3", "key2": "value2", "key1": "value1"}, "objectType": "Activity"}')

    def test_get_crp_multiple_choice(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foof',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'multiple-choice','correctResponsesPattern': ['golf', 'tetris'],'choices':
                [{'id': 'golf', 'description': {'en-US':'Golf Example'}},{'id': 'tetris',
                'description':{'en-US': 'Tetris Example'}}, {'id':'facebook', 'description':{'en-US':'Facebook App'}},
                {'id':'scrabble', 'description': {'en-US': 'Scrabble Example'}}]}}))        
        response = self.client.get(reverse(views.activities), {'activityId':'foof'})
        self.assertEqual(response.content, '{"choices": [{"id": "golf", "description": "{\\"en-US\\": \\"Golf Example\\"}"}, {"id": "tetris", "description": "{\\"en-US\\": \\"Tetris Example\\"}"}, {"id": "facebook", "description": "{\\"en-US\\": \\"Facebook App\\"}"}, {"id": "scrabble", "description": "{\\"en-US\\": \\"Scrabble Example\\"}"}], "definition": {"interactionType": "multiple-choice", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "fooe", "correctResponsesPattern": ["golf", "tetris"], "objectType": "Activity"}')

    def test_get_crp_true_false(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'fooe',
        'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
        'interactionType': 'true-false','correctResponsesPattern': ['true']}}))
        response = self.client.get(reverse(views.activities), {'activityId': 'fooe'})
        self.assertEqual(response.content, '{"definition": {"interactionType": "true-false", "type": "cmi.interaction", "name": "testname2", "description": "testdesc2"}, "activity_id": "fooe", "correctResponsesPattern": ["true"], "objectType": "Activity"}')

    #def test_get_crp_fill_in(self):


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

