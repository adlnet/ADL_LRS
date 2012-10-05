from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import views, models
from os import path
import sys
import json
from lrs.objects import Activity
import pdb

class ActivityTests(TestCase):
    
    def test_get(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity', 'id':'foobar'}))
        response = self.client.get(reverse(views.activities), {'activityId':'foobar'})
        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar', rsp)
        self.assertIn('Activity', rsp)
        self.assertIn('objectType', rsp)        


    def test_get_def(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar1',
                'definition': {'name': {'en-US':'testname'},'description': {'en-US':'testdesc'},
                'type': 'course','interactionType': 'intType'}})) 
        response = self.client.get(reverse(views.activities), {'activityId':'foobar1'})
        rsp = response.content

        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar1', rsp)
        self.assertIn('course', rsp)
        self.assertIn('intType', rsp)
        self.assertIn('en-US', rsp)
        self.assertIn('testname', rsp)
        self.assertIn('testdesc', rsp)
        
    def test_get_ext(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar2',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'course','interactionType': 'intType2', 
                'extensions': {'key1': 'value1', 'key2': 'value2'}}}))

        response = self.client.get(reverse(views.activities), {'activityId':'foobar2'})
        rsp = response.content

        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar2', rsp)
        self.assertIn('course', rsp)
        self.assertIn('intType2', rsp)
        self.assertIn('en-FR', rsp)
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('key1', rsp)
        self.assertIn('key2', rsp)
        self.assertIn('value1', rsp)
        self.assertIn('value2', rsp)

    def test_get_crp_multiple_choice(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar3',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'cmi.interaction','interactionType': 'multiple-choice',
                'correctResponsesPattern': ['golf', 'tetris'],'choices':[{'id': 'golf',
                'description': {'en-US':'Golf Example'}},{'id': 'tetris',
                'description':{'en-US': 'Tetris Example'}}, {'id':'facebook',
                'description':{'en-US':'Facebook App'}},{'id':'scrabble', 
                'description': {'en-US': 'Scrabble Example'}}]}}))        
        
        response = self.client.get(reverse(views.activities), {'activityId':'foobar3'})

        rsp = response.content
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar3', rsp)
        self.assertIn('cmi.interaction', rsp)
        self.assertIn('multiple-choice', rsp)
        self.assertIn('en-FR', rsp)
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('golf', rsp)
        self.assertIn('tetris', rsp)
        self.assertIn('Golf Example', rsp)
        self.assertIn('Tetris Example', rsp)
        self.assertIn('Facebook App', rsp)
        self.assertIn('Scrabble Example', rsp)
        self.assertIn('scrabble', rsp)
        self.assertIn('facebook', rsp)



    def test_get_crp_true_false(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar4',
        'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'},
        'type': 'cmi.interaction','interactionType': 'true-false','correctResponsesPattern': ['true']}}))
        
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar4'})

        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar4', rsp)
        self.assertIn('cmi.interaction', rsp)
        self.assertIn('true-false', rsp)
        self.assertIn('en-US', rsp)
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctresponsespattern', rsp)
        self.assertIn('true', rsp)

    def test_get_crp_fill_in(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar5',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'},
                'type': 'cmi.interaction','interactionType': 'fill-in',
                'correctResponsesPattern': ['Fill in answer']}}))
        # pdb.set_trace()
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar5'})       

        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar5', rsp)
        self.assertIn('cmi.interaction', rsp)
        self.assertIn('fill-in', rsp)
        self.assertIn('en-US', rsp)
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctresponsespattern', rsp)
        self.assertIn('Fill in answer', rsp)

    def test_get_crp_long_fill_in(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar6',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'cmi.interaction','interactionType': 'fill-in','correctResponsesPattern': ['Long fill in answer']}}))        

        response = self.client.get(reverse(views.activities), {'activityId': 'foobar6'})       

        rsp = response.content
        # pdb.set_trace()
        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar6', rsp)
        self.assertIn('cmi.interaction', rsp)
        self.assertIn('fill-in', rsp)
        self.assertIn('en-FR', rsp)
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctresponsespattern', rsp)
        self.assertIn('Long fill in answer', rsp)

    def test_get_crp_likert(self):
        act = Activity.Activity(json.dumps({'objectType': 'Still gonna be activity', 'id':'foobar7',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'}, 'type': 'cmi.interaction',
                'interactionType': 'likert','correctResponsesPattern': ['likert_3'],
                'scale':[{'id': 'likert_0', 'description': {'en-US':'Its OK'}},{'id': 'likert_1',
                'description':{'en-US': 'Its Pretty Cool'}}, {'id':'likert_2', 'description':{'en-US':'Its Cool Cool'}},
                {'id':'likert_3', 'description': {'en-US': 'Its Gonna Change the World'}}]}}))

        response = self.client.get(reverse(views.activities), {'activityId': 'foobar7'})       

        rsp = response.content
        # pdb.set_trace()
        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar7', rsp)
        self.assertIn('cmi.interaction', rsp)
        self.assertIn('likert', rsp)
        self.assertIn('en-US', rsp)
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctresponsespattern', rsp)
        self.assertIn('likert_3', rsp)
        self.assertIn('likert_2', rsp)
        self.assertIn('likert_1', rsp)

    def test_get_crp_matching(self):
        act = Activity.Activity(json.dumps({'objectType': 'Still gonna be activity', 'id':'foobar8',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'cmi.interaction','interactionType': 'matching',
                'correctResponsesPattern': ['lou.3,tom.2,andy.1'],'source':[{'id': 'lou',
                'description': {'en-US':'Lou'}},{'id': 'tom','description':{'en-US': 'Tom'}},
                {'id':'andy', 'description':{'en-US':'Andy'}}],'target':[{'id':'1',
                'description':{'en-US': 'SCORM Engine'}},{'id':'2','description':{'en-US': 'Pure-sewage'}},
                {'id':'3', 'description':{'en-US': 'SCORM Cloud'}}]}}))        
        
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar8'})       
        # pdb.set_trace()
        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar8', rsp)
        self.assertIn('cmi.interaction', rsp)
        self.assertIn('matching', rsp)
        self.assertIn('en-FR', rsp)
        self.assertIn('en-US', rsp)        
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctresponsespattern', rsp)
        self.assertIn('lou.3,tom.2,andy.1', rsp)
        self.assertIn('source', rsp)
        self.assertIn('target', rsp)

    def test_get_crp_performance(self):
        act = Activity.Activity(json.dumps({'objectType': 'activity', 'id':'foobar9',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'}, 'type': 'cmi.interaction',
                'interactionType': 'performance','correctResponsesPattern': ['pong.1,dg.10,lunch.4'],
                'steps':[{'id': 'pong', 'description': {'en-US':'Net pong matches won'}},{'id': 'dg',
                'description':{'en-US': 'Strokes over par in disc golf at Liberty'}},
                {'id':'lunch', 'description':{'en-US':'Lunch having been eaten'}}]}}))
        
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar9'})       
        rsp = response.content
        # pdb.set_trace()

        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar9', rsp)
        self.assertIn('cmi.interaction', rsp)
        self.assertIn('performance', rsp)
        self.assertIn('steps', rsp)
        self.assertIn('en-US', rsp)        
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctresponsespattern', rsp)
        self.assertIn('pong.1,dg.10,lunch.4', rsp)
        self.assertIn('Strokes over par in disc golf at Liberty', rsp)
        self.assertIn('Lunch having been eaten', rsp)

    def test_get_crp_sequencing(self):
        act = Activity.Activity(json.dumps({'objectType': 'activity', 'id':'foobar10',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'}, 'type': 'cmi.interaction',
                'interactionType': 'sequencing','correctResponsesPattern': ['lou,tom,andy,aaron'],
                'choices':[{'id': 'lou', 'description': {'en-US':'Lou'}},{'id': 'tom','description':{'en-US': 'Tom'}},
                {'id':'andy', 'description':{'en-US':'Andy'}},{'id':'aaron', 'description':{'en-US':'Aaron'}}]}}))        
        
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar10'})       
        rsp = response.content
        # pdb.set_trace()

        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar10', rsp)
        self.assertIn('cmi.interaction', rsp)
        self.assertIn('sequencing', rsp)
        self.assertIn('choices', rsp)
        self.assertIn('en-US', rsp)        
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctresponsespattern', rsp)
        self.assertIn('lou,tom,andy,aaron', rsp)

    def test_get_crp_numeric(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foobar11',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'}, 'type': 'cmi.interaction',
                'interactionType': 'numeric','correctResponsesPattern': ['4'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))        

        response = self.client.get(reverse(views.activities), {'activityId': 'foobar11'})       
        rsp = response.content
        # pdb.set_trace()

        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar11', rsp)
        self.assertIn('cmi.interaction', rsp)
        self.assertIn('numeric', rsp)
        self.assertIn('4', rsp)
        self.assertIn('en-US', rsp)        
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctresponsespattern', rsp)
        self.assertIn('extensions', rsp)
        self.assertIn('key1', rsp)
        self.assertIn('value1', rsp)
        self.assertIn('key2', rsp)
        self.assertIn('value2', rsp)
        self.assertIn('key3', rsp)
        self.assertIn('value3', rsp)                                

    def test_get_crp_other(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id': 'foobar12',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'},
                'type': 'cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35.937432,-86.868896)']}}))        
        
        response = self.client.get(reverse(views.activities), {'activityId': 'foobar12'})       
        rsp = response.content

        self.assertEqual(response.status_code, 200)
        self.assertIn('foobar12', rsp)
        self.assertIn('cmi.interaction', rsp)
        self.assertIn('other', rsp)
        self.assertIn('(35.937432,-86.868896)', rsp)
        self.assertIn('en-US', rsp)        
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctresponsespattern', rsp)


    def test_get_wrong_activity(self):
        response = self.client.get(reverse(views.activities), {'activityId': 'foo'})
        rsp = response.content

        self.assertEqual(response.status_code, 200)
        self.assertEqual(rsp, '[]')

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

