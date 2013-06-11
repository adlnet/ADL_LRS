import base64
import json
from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import views
from lrs.objects.ActivityManager import ActivityManager


class ActivityTests(TestCase):
    def setUp(self):
        self.username = "tester"
        self.email = "test@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {'username':self.username, 'email': self.email,'password':self.password,'password2':self.password}
        response = self.client.post(reverse(views.register),form, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def test_get(self):
        act = ActivityManager(json.dumps({'objectType':'Activity', 'id':'act:foobar'}))
        response = self.client.get(reverse(views.activities), {'activityId':'act:foobar'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar', rsp)
        self.assertIn('Activity', rsp)
        self.assertIn('objectType', rsp)        
        self.assertIn('content-length', response._headers)
        
    def test_head(self):
        act = ActivityManager(json.dumps({'objectType':'Activity', 'id':'act:foobar'}))
        response = self.client.head(reverse(views.activities), {'activityId':'act:foobar'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '')
        self.assertIn('content-length', response._headers)

    def test_get_def(self):
        act = ActivityManager(json.dumps({'objectType': 'Activity', 'id':'act:foobar1',
                'definition': {'name': {'en-US':'testname', 'en-GB': 'altname'},
                'description': {'en-US':'testdesc', 'en-GB': 'altdesc'},
                'type': 'type:course','interactionType': 'intType'}})) 
        response = self.client.get(reverse(views.activities), {'activityId':'act:foobar1'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar1', rsp)
        self.assertIn('type:course', rsp)
        self.assertIn('intType', rsp)
        self.assertIn('en-US', rsp)
        self.assertIn('testname', rsp)
        self.assertIn('testdesc', rsp)
        self.assertIn('en-GB', rsp)
        self.assertIn('altdesc', rsp)
        self.assertIn('altname', rsp)
        
    def test_get_ext(self):
        act = ActivityManager(json.dumps({'objectType': 'Activity', 'id':'act:foobar2',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'type:course','interactionType': 'intType2', 
                'extensions': {'ext:key1': 'value1', 'ext:key2': 'value2'}}}))

        response = self.client.get(reverse(views.activities), {'activityId':'act:foobar2'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar2', rsp)
        self.assertIn('type:course', rsp)
        self.assertIn('intType2', rsp)
        self.assertIn('en-FR', rsp)
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('key1', rsp)
        self.assertIn('key2', rsp)
        self.assertIn('value1', rsp)
        self.assertIn('value2', rsp)

    def test_get_crp_multiple_choice(self):
        act = ActivityManager(json.dumps({'objectType': 'Activity', 'id':'act:foobar3',
                'definition': {'name': {'en-FR':'testname2'},
                'description': {'en-FR':'testdesc2', 'en-CH': 'altdesc'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'choice',
                'correctResponsesPattern': ['golf', 'tetris'],'choices':[{'id': 'golf',
                'description': {'en-US':'Golf Example', 'en-GB':'alt golf'}},{'id': 'tetris',
                'description':{'en-US': 'Tetris Example'}}, {'id':'facebook',
                'description':{'en-US':'Facebook App'}},{'id':'scrabble', 
                'description': {'en-US': 'Scrabble Example'}}]}}))        
        
        response = self.client.get(reverse(views.activities), {'activityId':'act:foobar3'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")

        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar3', rsp)
        self.assertIn('http://adlnet.gov/expapi/activities/cmi.interaction', rsp)
        self.assertIn('choice', rsp)
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
        self.assertIn('en-GB', rsp)
        self.assertIn('alt golf', rsp)
        self.assertIn('en-CH', rsp)
        self.assertIn('altdesc', rsp)

    def test_get_crp_true_false(self):
        act = ActivityManager(json.dumps({'objectType': 'Activity', 'id':'act:foobar4',
        'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'},
        'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'true-false','correctResponsesPattern': ['true']}}))
        
        response = self.client.get(reverse(views.activities), {'activityId': 'act:foobar4'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")

        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar4', rsp)
        self.assertIn('http://adlnet.gov/expapi/activities/cmi.interaction', rsp)
        self.assertIn('true-false', rsp)
        self.assertIn('en-US', rsp)
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctResponsesPattern', rsp)
        self.assertIn('true', rsp)

    def test_get_crp_fill_in(self):
        act = ActivityManager(json.dumps({'objectType': 'Activity', 'id':'act:foobar5',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'fill-in',
                'correctResponsesPattern': ['Fill in answer']}}))

        response = self.client.get(reverse(views.activities), {'activityId': 'act:foobar5'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")       

        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar5', rsp)
        self.assertIn('http://adlnet.gov/expapi/activities/cmi.interaction', rsp)
        self.assertIn('fill-in', rsp)
        self.assertIn('en-US', rsp)
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctResponsesPattern', rsp)
        self.assertIn('Fill in answer', rsp)

    def test_get_crp_long_fill_in(self):
        act = ActivityManager(json.dumps({'objectType': 'Activity', 'id':'act:foobar6',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'fill-in',
                'correctResponsesPattern': ['Long fill in answer']}}))        

        response = self.client.get(reverse(views.activities), {'activityId': 'act:foobar6'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")       

        rsp = response.content

        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar6', rsp)
        self.assertIn('http://adlnet.gov/expapi/activities/cmi.interaction', rsp)
        self.assertIn('fill-in', rsp)
        self.assertIn('en-FR', rsp)
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctResponsesPattern', rsp)
        self.assertIn('Long fill in answer', rsp)

    def test_get_crp_likert(self):
        act = ActivityManager(json.dumps({'objectType': 'Still gonna be activity', 'id':'act:foobar7',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'likert','correctResponsesPattern': ['likert_3'],
                'scale':[{'id': 'likert_0', 'description': {'en-US':'Its OK'}},{'id': 'likert_1',
                'description':{'en-US': 'Its Pretty Cool'}}, {'id':'likert_2',
                'description':{'en-US':'Its Cool Cool'}},{'id':'likert_3',
                'description': {'en-US': 'Its Gonna Change the World'}}]}}))

        response = self.client.get(reverse(views.activities), {'activityId': 'act:foobar7'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")       

        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar7', rsp)
        self.assertIn('http://adlnet.gov/expapi/activities/cmi.interaction', rsp)
        self.assertIn('likert', rsp)
        self.assertIn('en-US', rsp)
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctResponsesPattern', rsp)
        self.assertIn('likert_3', rsp)
        self.assertIn('likert_2', rsp)
        self.assertIn('likert_1', rsp)

    def test_get_crp_matching(self):
        act = ActivityManager(json.dumps({'objectType': 'Still gonna be activity', 'id':'act:foobar8',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'matching',
                'correctResponsesPattern': ['lou.3,tom.2,andy.1'],'source':[{'id': 'lou',
                'description': {'en-US':'Lou'}},{'id': 'tom','description':{'en-US': 'Tom'}},
                {'id':'andy', 'description':{'en-US':'Andy'}}],'target':[{'id':'1',
                'description':{'en-US': 'SCORM Engine'}},{'id':'2','description':{'en-US': 'Pure-sewage'}},
                {'id':'3', 'description':{'en-US': 'SCORM Cloud'}}]}}))        
        
        response = self.client.get(reverse(views.activities), {'activityId': 'act:foobar8'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")       
        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar8', rsp)
        self.assertIn('http://adlnet.gov/expapi/activities/cmi.interaction', rsp)
        self.assertIn('matching', rsp)
        self.assertIn('en-FR', rsp)
        self.assertIn('en-US', rsp)        
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctResponsesPattern', rsp)
        self.assertIn('lou.3,tom.2,andy.1', rsp)
        self.assertIn('source', rsp)
        self.assertIn('target', rsp)

    def test_get_crp_performance(self):
        act = ActivityManager(json.dumps({'objectType': 'activity', 'id':'act:foobar9',
                'definition': {'name': {'en-US':'testname2', 'en-GB': 'altname'},
                'description': {'en-US':'testdesc2'},'type': 'http://adlnet.gov/expapi/activities/cmi.interaction',
                'interactionType': 'performance',
                'correctResponsesPattern': ['pong.1,dg.10,lunch.4'],'steps':[{'id': 'pong',
                'description': {'en-US':'Net pong matches won'}},{'id': 'dg',
                'description':{'en-US': 'Strokes over par in disc golf at Liberty'}},
                {'id':'lunch', 'description':{'en-US':'Lunch having been eaten', 
                'en-FR': 'altlunch'}}]}}))
        
        response = self.client.get(reverse(views.activities), {'activityId': 'act:foobar9'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")       
        rsp = response.content
        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar9', rsp)
        self.assertIn('http://adlnet.gov/expapi/activities/cmi.interaction', rsp)
        self.assertIn('performance', rsp)
        self.assertIn('steps', rsp)
        self.assertIn('en-US', rsp)        
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctResponsesPattern', rsp)
        self.assertIn('pong.1,dg.10,lunch.4', rsp)
        self.assertIn('Strokes over par in disc golf at Liberty', rsp)
        self.assertIn('Lunch having been eaten', rsp)
        self.assertIn('en-GB', rsp)
        self.assertIn('en-FR', rsp)
        self.assertIn('altlunch', rsp)

    def test_get_crp_sequencing(self):
        act = ActivityManager(json.dumps({'objectType': 'activity', 'id':'act:foobar10',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'sequencing',
                'correctResponsesPattern': ['lou,tom,andy,aaron'],'choices':[{'id': 'lou',
                'description': {'en-US':'Lou'}},{'id': 'tom','description':{'en-US': 'Tom'}},
                {'id':'andy', 'description':{'en-US':'Andy'}},{'id':'aaron', 'description':{'en-US':'Aaron'}}]}}))        
        
        response = self.client.get(reverse(views.activities), {'activityId': 'act:foobar10'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")       
        rsp = response.content

        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar10', rsp)
        self.assertIn('http://adlnet.gov/expapi/activities/cmi.interaction', rsp)
        self.assertIn('sequencing', rsp)
        self.assertIn('choices', rsp)
        self.assertIn('en-US', rsp)        
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctResponsesPattern', rsp)
        self.assertIn('lou,tom,andy,aaron', rsp)

    def test_get_crp_numeric(self):
        act = ActivityManager(json.dumps({'objectType': 'Activity', 'id':'act:foobar11',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'numeric','correctResponsesPattern': ['4'],
                'extensions': {'ext:key1': 'value1', 'ext:key2': 'value2','ext:key3': 'value3'}}}))        

        response = self.client.get(reverse(views.activities), {'activityId': 'act:foobar11'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")       
        rsp = response.content

        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar11', rsp)
        self.assertIn('http://adlnet.gov/expapi/activities/cmi.interaction', rsp)
        self.assertIn('numeric', rsp)
        self.assertIn('4', rsp)
        self.assertIn('en-US', rsp)        
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctResponsesPattern', rsp)
        self.assertIn('extensions', rsp)
        self.assertIn('key1', rsp)
        self.assertIn('value1', rsp)
        self.assertIn('key2', rsp)
        self.assertIn('value2', rsp)
        self.assertIn('key3', rsp)
        self.assertIn('value3', rsp)                                

    def test_get_crp_other(self):
        act = ActivityManager(json.dumps({'objectType': 'Activity', 'id': 'act:foobar12',
                'definition': {'name': {'en-US':'testname2'},'description': {'en-US':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other',
                'correctResponsesPattern': ['(35.937432,-86.868896)']}}))        
        
        response = self.client.get(reverse(views.activities), {'activityId': 'act:foobar12'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")       
        rsp = response.content

        self.assertEqual(response.status_code, 200)
        self.assertIn('act:foobar12', rsp)
        self.assertIn('http://adlnet.gov/expapi/activities/cmi.interaction', rsp)
        self.assertIn('other', rsp)
        self.assertIn('(35.937432,-86.868896)', rsp)
        self.assertIn('en-US', rsp)        
        self.assertIn('testname2', rsp)
        self.assertIn('testdesc2', rsp)
        self.assertIn('correctResponsesPattern', rsp)


    def test_get_wrong_activity(self):
        response = self.client.get(reverse(views.activities), {'activityId': 'act:act:foo'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        rsp = response.content

        self.assertEqual(response.status_code, 404)

    def test_head_wrong_activity(self):
        response = self.client.head(reverse(views.activities), {'activityId': 'act:act:foo'}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 404)

    def test_get_no_activity(self):
        response = self.client.get(reverse(views.activities), Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 400)
    
    def test_post(self):
        response = self.client.post(reverse(views.activities), {'activityId':'act:my_activity'},
            content_type='application/x-www-form-urlencoded', Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 405)

    def test_delete(self):
        response = self.client.delete(reverse(views.activities), {'activityId':'act:my_activity'},
            content_type='application/x-www-form-urlencoded', Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 405)

    def test_put(self):
        response = self.client.put(reverse(views.activities), {'activityId':'act:my_activity'},
            content_type='application/x-www-form-urlencoded', Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 405)

