from django.test import TestCase
from django.test.utils import setup_test_environment
from lrs import models
import json
from django.core.exceptions import ValidationError
import urllib
from os import path
import sys
from lrs.objects import Activity


class ActivityModelsTests(TestCase):
    #Called on all activity objects to see if they were created with the correct fields
    def do_activity_object(self,act, act_id, objType):
        self.assertEqual(act.activity.activity_id, act_id)
        self.assertEqual(act.activity.objectType, objType)
        
    #Called on all activity django models to see if they were created with the correct fields    
    def do_activity_model(self,realid,act_id, objType):
        self.assertEqual(models.activity.objects.filter(id=realid)[0].objectType, objType)
        self.assertEqual(models.activity.objects.filter(id=realid)[0].activity_id, act_id)

    #Called on all activity objects with definitions to see if they were created with the correct fields
    def do_activity_definition_object(self, act, name, desc, course, intType):
        self.assertEqual(act.activity.activity_definition.name, name)
        self.assertEqual(act.activity.activity_definition.description, desc)
        self.assertEqual(act.activity.activity_definition.activity_definition_type, course)
        self.assertEqual(act.activity.activity_definition.interactionType, intType)

    #Called on all activity django models with definitions to see if they were created with the correct fields
    def do_activity_definition_model(self, PK, testname, testdesc, course, intType):
        self.assertEqual(models.activity_definition.objects.get(activity=PK).name, testname)
        self.assertEqual(models.activity_definition.objects.get(activity=PK).description, testdesc)
        self.assertEqual(models.activity_definition.objects.get(activity=PK).activity_definition_type, course)
        self.assertEqual(models.activity_definition.objects.get(activity=PK).interactionType, intType)

    #Called on all activity objects with extensions to see if they were created with the correct fields and values
    #All extensions are created with the same three values and keys
    def do_activity_definition_extensions_object(self, act, key1, key2, key3, value1, value2, value3):
        self.assertEqual(act.activity_definition_extensions[0].key, key3)
        self.assertEqual(act.activity_definition_extensions[1].key, key2)
        self.assertEqual(act.activity_definition_extensions[2].key, key1)

        self.assertEqual(act.activity_definition_extensions[0].value, value3)    
        self.assertEqual(act.activity_definition_extensions[1].value, value2)
        self.assertEqual(act.activity_definition_extensions[2].value, value1)        

    #Called on all activity django models with extensions to see if they were created with the correct fields and values
    #All extensions are created with the same three values and keys
    def do_activity_definition_extensions_model(self, defPK, key1, key2, key3, value1, value2, value3):
        #Create list comprehesions to easier assess keys and values
        extList = models.activity_extensions.objects.values_list().filter(activity_definition=defPK)
        extKeys = [ext[1] for ext in extList]
        extVals = [ext[2] for ext in extList]

        self.assertIn(key1, extKeys)
        self.assertIn(key2, extKeys)
        self.assertIn(key3, extKeys)
        self.assertIn(value1, extVals)
        self.assertIn(value2, extVals)
        self.assertIn(value3, extVals)

    #call on all activity objects with a correctResponsePattern because of cmi.interaction type
    def do_activity_definition_correctResponsePattern_object(self, act, defPK, rspPK, answer):
        self.assertIn(act.correctResponsesPattern.activity_definition, defPK)
        self.assertIn(rspPK[0].activity_definition, defPK)
        self.assertEqual(act.answers[0].answer, answer)

    #Called on all activity django models with a correctResponsePattern because of cmi.interaction type
    def do_activity_definition_correctResponsePattern_model(self, rspPK, answers):
        rspAnswers = models.correctresponsespattern_answer.objects.values_list('answer', flat=True).filter(correctresponsespattern=rspPK)
        
        for answer in answers:
            self.assertIn(answer,rspAnswers)

    #Called on all activity django models with choices because of sequence and choice interactionType
    def do_actvity_definition_choices_model(self, defPK, clist, dlist):
        descs = models.activity_definition_choice.objects.values_list('description', flat=True).filter(activity_definition=defPK)
        choices = models.activity_definition_choice.objects.values_list('choice_id', flat=True).filter(activity_definition=defPK)
        
        for c in clist:
            self.assertIn(c,choices)

        for d in dlist:
            self.assertIn(d, descs)

    #Called on all activity django models with scale because of likert interactionType
    def do_actvity_definition_likert_model(self, defPK, clist, dlist):
        descs = models.activity_definition_scale.objects.values_list('description', flat=True).filter(activity_definition=defPK)
        choices = models.activity_definition_scale.objects.values_list('scale_id', flat=True).filter(activity_definition=defPK)
        
        for c in clist:
            self.assertIn(c,choices)

        for d in dlist:
            self.assertIn(d, descs)

    #Called on all activity django models with steps because of performance interactionType
    def do_actvity_definition_performance_model(self, defPK, slist, dlist):
        descs = models.activity_definition_step.objects.values_list('description', flat=True).filter(activity_definition=defPK)
        steps = models.activity_definition_step.objects.values_list('step_id', flat=True).filter(activity_definition=defPK)
        
        for s in slist:
            self.assertIn(s,steps)

        for d in dlist:
            self.assertIn(d, descs)

    #Called on all activity django models with source and target because of matching interactionType
    def do_actvity_definition_matching_model(self, defPK, source_id_list, source_desc_list, target_id_list, target_desc_list):
        source_descs = models.activity_definition_source.objects.values_list('description', flat=True).filter(activity_definition=defPK)
        sources = models.activity_definition_source.objects.values_list('source_id', flat=True).filter(activity_definition=defPK)
        
        target_descs = models.activity_definition_target.objects.values_list('description', flat=True).filter(activity_definition=defPK)
        targets = models.activity_definition_target.objects.values_list('target_id', flat=True).filter(activity_definition=defPK)
        
        for s_id in source_id_list:
            self.assertIn(s_id,sources)

        for s_desc in source_desc_list:
            self.assertIn(s_desc, source_descs)

        for t_id in target_id_list:
            self.assertIn(t_id,targets)

        for t_desc in target_desc_list:
            self.assertIn(t_desc, target_descs)            


    #Test activity that doesn't have a def, isn't a link and resolves (will not create Activity object)
    def test_activity_no_def_not_link_resolve(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id': 'http://yahoo.com'}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://yahoo.com')

    #Test activity that doesn't have a def, isn't a link and doesn't resolve (creates useless Activity object)
    def test_activity_no_def_not_link_no_resolve(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity', 'id':'foo'}))
        
        self.do_activity_object(act,'foo','Activity')
        self.do_activity_model(act.activity.id, 'foo', 'Activity')

    #Test activity that doesn't have a def, isn't a link and conforms to schema (populates everything from XML)
    def test_activity_no_def_not_link_schema_conform(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'http://localhost:8000/TCAPI/tcexample/'}))

        PK = models.activity.objects.filter(id=act.activity.id)
        
        self.do_activity_object(act,'http://localhost:8000/TCAPI/tcexample/', 'Activity')
        self.do_activity_definition_object(act, 'Example Name', 'Example Desc', 'module', 'course')
        self.do_activity_model(act.activity.id, 'http://localhost:8000/TCAPI/tcexample/', 'Activity')        
        self.do_activity_definition_model(PK, 'Example Name', 'Example Desc', 'module', 'course')

    #Test activity that doesn't have a def, isn't a link and conforms to schema but ID already exists (won't create it)
    def test_activity_no_def_not_link_schema_conform1(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'http://localhost:8000/TCAPI/tcexample/'}))
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id': 'http://localhost:8000/TCAPI/tcexample/'}))

    # def test_multiple_activities(self):
    #     act1 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'foob'}))
    #     act2 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'foob'}))
    #     print act1.activity.__dict__
    #     print act2.activity.__dict__

    '''
    Choices is not part of the XML schema for now, so this will throw an exception
    #Test activity that doesn't have a def, isn't a link and conforms to schema with CRP (populates everything from XML)
    def test_activity_no_def_not_link_schema_conform_correctResponsesPattern(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'http://localhost:8000/TCAPI/tcexample3/'}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act,'http://localhost:8000/TCAPI/tcexample3/', 'Activity')
        self.do_activity_definition_object(act, 'Example Name', 'Example Desc', 'cmi.interaction', 'multiple-choice')
        self.do_activity_model(act.activity.id, 'http://localhost:8000/TCAPI/tcexample3/', 'Activity')        
        self.do_activity_definition_model(PK, 'Example Name', 'Example Desc', 'cmi.interaction', 'multiple-choice')
    
        self.assertEqual(act.answers[0].answer, 'golf')
        self.assertEqual(act.answers[1].answer, 'tetris')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['golf', 'tetris'])
    '''

    #Test activity that doesn't have a def, isn't a link and conforms to schema with extensions (populates everything from XML)
    def test_activity_no_def_not_link_schema_conform_extensions(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'http://localhost:8000/TCAPI/tcexample2/'}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)

        self.do_activity_object(act,'http://localhost:8000/TCAPI/tcexample2/', 'Activity')
        self.do_activity_definition_object(act, 'Example Name', 'Example Desc', 'module', 'course')
        self.do_activity_model(act.activity.id, 'http://localhost:8000/TCAPI/tcexample2/', 'Activity')        
        self.do_activity_definition_model(PK, 'Example Name', 'Example Desc', 'module', 'course')

        self.do_activity_definition_extensions_object(act, 'keya', 'keyb', 'keyc', 'first value', 'second value', 'third value')
        self.do_activity_definition_extensions_model(defPK, 'keya', 'keyb', 'keyc','first value', 'second value', 'third value')

    #Test an activity that has a def,is not a link yet the ID resolves, but doesn't conform to XML schema (will not create one)
    def test_activity_not_link_resolve(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id': 'http://tincanapi.wikispaces.com',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'course',
                'interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://tincanapi.wikispaces.com')

    #Test an activity that has a def, not a link and the provided ID doesn't resolve (should still use values from JSON)
    def test_activity_not_link_no_resolve(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'/var/www/adllrs/activity/example.xml',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'course',
                'interactionType': 'intType'}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        
        self.do_activity_object(act, '/var/www/adllrs/activity/example.xml', 'Activity')
        self.do_activity_definition_object(act, 'testname', 'testdesc', 'course', 'intType')
        self.do_activity_model(act.activity.id, '/var/www/adllrs/activity/example.xml', 'Activity')        
        self.do_activity_definition_model(PK, 'testname', 'testdesc', 'course', 'intType')

    #Test an activity that has a def, not a link and the provided ID conforms to the schema (should use values from XML and override JSON)
    def test_activity_not_link_schema_conform(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'http://localhost:8000/TCAPI/tcexample4/',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'course',
                'interactionType': 'intType'}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        
        self.do_activity_object(act, 'http://localhost:8000/TCAPI/tcexample4/', 'Activity')
        self.do_activity_definition_object(act, 'Example Name', 'Example Desc', 'module', 'course')
        self.do_activity_model(act.activity.id, 'http://localhost:8000/TCAPI/tcexample4/', 'Activity')        
        self.do_activity_definition_model(PK, 'Example Name', 'Example Desc', 'module', 'course')

    #Test an activity that has a def, is a link and the ID resolves (should use values from JSON)
    def test_activity_link_resolve(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id': 'http://localhost:8000/TCAPI/',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'link',
                'interactionType': 'intType'}}))


        PK = models.activity.objects.filter(id=act.activity.id)
        
        self.do_activity_object(act, 'http://localhost:8000/TCAPI/', 'Activity')
        self.do_activity_definition_object(act, 'testname', 'testdesc', 'link', 'intType')
        self.do_activity_model(act.activity.id, 'http://localhost:8000/TCAPI/', 'Activity')        
        self.do_activity_definition_model(PK, 'testname', 'testdesc', 'link', 'intType')

    #Test an activity that has a def, is a link and the ID does not resolve (will not create one)
    def test_activity_link_no_resolve(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id': 'http://foo',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'link',
                'interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://foo')

    #Throws exception because incoming data is not JSON
    def test_activity_not_json(self):
        self.assertRaises(Exception, Activity.Activity,"This string should throw exception since it's not JSON")

    #Test an activity where there is no given objectType, won't be created with one
    def test_activity_no_objectType(self):
        act = Activity.Activity(json.dumps({'id':'fooa'}))
        
        self.do_activity_object(act,'fooa', None)
        self.do_activity_model(act.activity.id,'fooa', None)

    #Test an activity with a provided objectType but http://localhost:8000/TCAPI/tcexample4/    def test_activity_wrong_objectType(self):
        act = Activity.Activity(json.dumps({'id': 'foob', 'objectType':'Wrong'}))    

        self.do_activity_object(act,'foob', 'Activity')
        self.do_activity_model(act.activity.id, 'foob', 'Activity')

    #Test activity where given URL doesn't resolve
    def test_activity_invalid_activity_id(self):
        self.assertRaises(ValidationError, Activity.Activity, json.dumps({'id': 'http://foo', 'objectType':'Activity',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'link',
                'interactionType': 'intType'}}))

    #Test activity with definition - must retrieve activity object in order to test definition from DB
    def test_activity_definition(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'fooc',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'course',
                'interactionType': 'intType'}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        
        self.do_activity_object(act,'fooc', 'Activity')
        self.do_activity_definition_object(act, 'testname', 'testdesc', 'course', 'intType')
        self.do_activity_model(act.activity.id,'fooc', 'Activity')        
        self.do_activity_definition_model(PK, 'testname', 'testdesc', 'course', 'intType')

    #Test activity with definition given wrong type (won't create it)
    def test_activity_definition_wrong_type(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity',
                'id':'http://msn.com','definition': {'NAME': 'testname',
                'descripTION': 'testdesc', 'tYpe': 'wrong','interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://msn.com')
    
    #Test activity with definition missing name in definition (won't create it)
    def test_activity_definition_required_fields(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity',
                'id':'http://google.com','definition': {'description': 'testdesc',
                'type': 'wrong','interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://google.com')

    #Test activity with definition that contains extensions - need to retrieve activity and activity definition objects in order to test extenstions
    def test_activity_definition_extensions(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'food',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'course',
                'interactionType': 'intType2', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)

        self.do_activity_object(act,'food', 'Activity')
        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'course', 'intType2')
        
        self.do_activity_model(act.activity.id,'food', 'Activity')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'course', 'intType2')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

    #Test activity with definition given wrong interactionType (won't create one)
    def test_activity_definition_wrong_interactionType(self):

        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id':'http://facebook.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'intType2', 'correctResponsesPatteRN': 'response', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))
     
        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://facebook.com')


    #Test activity with definition and valid interactionType-it must also provide the correctResponsesPattern field
    #(wont' create it)
    def test_activity_definition_no_correctResponsesPattern(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id':'http://twitter.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'true-false', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))
     
        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://twitter.com')

    #Test activity with definition that is cmi.interaction and true-false interactionType
    def test_activity_definition_cmiInteraction_true_false(self):

        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'fooe',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'true-false','correctResponsesPattern': ['true'] ,'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)


        self.do_activity_object(act,'fooe', 'Activity')
        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'true-false')
        
        self.do_activity_model(act.activity.id,'fooe', 'Activity')                
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'true-false')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, 'true')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['true'])
    
    #Test activity with definition that is cmi.interaction and multiple choice interactionType
    def test_activity_definition_cmiInteraction_multiple_choice(self):    
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foof',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'multiple-choice','correctResponsesPattern': ['golf', 'tetris'],
                'choices':[{'id': 'golf', 'description': {'en-US':'Golf Example'}},{'id': 'tetris',
                'description':{'en-US': 'Tetris Example'}}, {'id':'facebook', 'description':{'en-US':'Facebook App'}},
                {'id':'scrabble', 'description': {'en-US': 'Scrabble Example'}}],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act,'foof', 'Activity')
        self.do_activity_model(act.activity.id,'foof', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'multiple-choice')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'multiple-choice')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.assertEqual(act.answers[0].answer, 'golf')
        self.assertEqual(act.answers[1].answer, 'tetris')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['golf', 'tetris'])

        #Test object choice values
        self.assertEqual(act.choices[0].choice_id, 'golf')
        self.assertEqual(act.choices[0].description, '{"en-US": "Golf Example"}')

        self.assertEqual(act.choices[1].choice_id, 'tetris')
        self.assertEqual(act.choices[1].description, '{"en-US": "Tetris Example"}')
        
        self.assertEqual(act.choices[2].choice_id, 'facebook')
        self.assertEqual(act.choices[2].description, '{"en-US": "Facebook App"}')

        self.assertEqual(act.choices[3].choice_id, 'scrabble')
        self.assertEqual(act.choices[3].description, '{"en-US": "Scrabble Example"}')

        #Check model choice values
        clist = ['golf', 'tetris', 'facebook', 'scrabble']
        dlist = ['{"en-US": "Golf Example"}','{"en-US": "Tetris Example"}','{"en-US": "Facebook App"}','{"en-US": "Scrabble Example"}']
        self.do_actvity_definition_choices_model(defPK, clist, dlist)        
        
    #Test activity with definition that is cmi.interaction and multiple choice but missing choices (won't create it)
    def test_activity_definition_cmiInteraction_multiple_choice_no_choices(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id':'http://wikipedia.org',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'multiple-choice','correctResponsesPattern': ['golf', 'tetris'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))   

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://wikipedia.org')
    
    #Test activity with definition that is cmi.interaction and fill in interactionType
    def test_activity_definition_cmiInteraction_fill_in(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foog',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'fill-in','correctResponsesPattern': ['Fill in answer'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act,'foog', 'Activity')
        self.do_activity_model(act.activity.id,'foog', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, 'Fill in answer')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['Fill in answer'])

    #Test activity with definition that is cmi.interaction and long fill in interactionType
    def test_activity_definition_cmiInteraction_long_fill_in(self):

        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'fooh',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'fill-in','correctResponsesPattern': ['Long fill in answer'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'fooh', 'Activity')
        self.do_activity_model(act.activity.id, 'fooh', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, 'Long fill in answer')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['Long fill in answer'])

    #Test activity with definition that is cmi.interaction and likert interactionType
    def test_activity_definition_cmiInteraction_likert(self):    
        act = Activity.Activity(json.dumps({'objectType': 'Still gonna be activity', 'id':'fooi',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'likert','correctResponsesPattern': ['likert_3'],
                'scale':[{'id': 'likert_0', 'description': {'en-US':'Its OK'}},{'id': 'likert_1',
                'description':{'en-US': 'Its Pretty Cool'}}, {'id':'likert_2', 'description':{'en-US':'Its Damn Cool'}},
                {'id':'likert_3', 'description': {'en-US': 'Its Gonna Change the World'}}]}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'fooi', 'Activity')
        self.do_activity_model(act.activity.id, 'fooi', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'likert')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'likert')

        self.assertEqual(act.answers[0].answer, 'likert_3')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['likert_3'])

        #Test object choice values
        self.assertEqual(act.scale_choices[0].scale_id, 'likert_0')
        self.assertEqual(act.scale_choices[0].description, '{"en-US": "Its OK"}')

        self.assertEqual(act.scale_choices[1].scale_id, 'likert_1')
        self.assertEqual(act.scale_choices[1].description, '{"en-US": "Its Pretty Cool"}')
        
        self.assertEqual(act.scale_choices[2].scale_id, 'likert_2')
        self.assertEqual(act.scale_choices[2].description, '{"en-US": "Its Damn Cool"}')

        self.assertEqual(act.scale_choices[3].scale_id, 'likert_3')
        self.assertEqual(act.scale_choices[3].description, '{"en-US": "Its Gonna Change the World"}')

        #Check model choice values
        clist = ['likert_3']
        dlist = ['{"en-US": "Its OK"}','{"en-US": "Its Pretty Cool"}','{"en-US": "Its Damn Cool"}','{"en-US": "Its Gonna Change the World"}']
        self.do_actvity_definition_likert_model(defPK, clist, dlist)

    #Test activity with definition that is cmi.interaction and matching interactionType
    def test_activity_definition_cmiInteraction_matching(self):    
        act = Activity.Activity(json.dumps({'objectType': 'Still gonna be activity', 'id':'fooj',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'matching','correctResponsesPattern': ['lou.3,tom.2,andy.1'],
                'source':[{'id': 'lou', 'description': {'en-US':'Lou'}},{'id': 'tom',
                'description':{'en-US': 'Tom'}}, {'id':'andy', 'description':{'en-US':'Andy'}}],
                'target':[{'id':'1', 'description':{'en-US': 'SCORM Engine'}},{'id':'2',
                'description':{'en-US': 'Pure-sewage'}},{'id':'3', 'description':{'en-US': 'SCORM Cloud'}}]}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'fooj', 'Activity')
        self.do_activity_model(act.activity.id, 'fooj', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'matching')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'matching')

        self.assertEqual(act.answers[0].answer, 'lou.3,tom.2,andy.1')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['lou.3,tom.2,andy.1'])

        #Test object choice values
        self.assertEqual(act.source_choices[0].source_id, 'lou')
        self.assertEqual(act.source_choices[0].description, '{"en-US": "Lou"}')

        self.assertEqual(act.source_choices[1].source_id, 'tom')
        self.assertEqual(act.source_choices[1].description, '{"en-US": "Tom"}')
        
        self.assertEqual(act.source_choices[2].source_id, 'andy')
        self.assertEqual(act.source_choices[2].description, '{"en-US": "Andy"}')

        self.assertEqual(act.target_choices[0].target_id, '1')
        self.assertEqual(act.target_choices[0].description, '{"en-US": "SCORM Engine"}')

        self.assertEqual(act.target_choices[1].target_id, '2')
        self.assertEqual(act.target_choices[1].description, '{"en-US": "Pure-sewage"}')
        
        self.assertEqual(act.target_choices[2].target_id, '3')
        self.assertEqual(act.target_choices[2].description, '{"en-US": "SCORM Cloud"}')

        #Check model choice values
        source_id_list = ['lou', 'tom', 'andy']
        source_desc_list = ['{"en-US": "Lou"}','{"en-US": "Tom"}','{"en-US": "Andy"}']
        target_id_list = ['1','2','3']
        target_desc_list = ['{"en-US": "SCORM Engine"}','{"en-US": "Pure-sewage"}','{"en-US": "SCORM Cloud"}']
        self.do_actvity_definition_matching_model(defPK, source_id_list, source_desc_list, target_id_list, target_desc_list)

    #Test activity with definition that is cmi.interaction and performance interactionType
    def test_activity_definition_cmiInteraction_performance(self):    
        act = Activity.Activity(json.dumps({'objectType': 'activity', 'id':'fook',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'performance','correctResponsesPattern': ['pong.1,dg.10,lunch.4'],
                'steps':[{'id': 'pong', 'description': {'en-US':'Net pong matches won'}},{'id': 'dg',
                'description':{'en-US': 'Strokes over par in disc golf at Liberty'}},
                {'id':'lunch', 'description':{'en-US':'Lunch having been eaten'}}]}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'fook', 'Activity')
        self.do_activity_model(act.activity.id, 'fook', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'performance')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'performance')

        self.assertEqual(act.answers[0].answer, 'pong.1,dg.10,lunch.4')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['pong.1,dg.10,lunch.4'])

        #Test object step values
        self.assertEqual(act.steps[0].step_id, 'pong')
        self.assertEqual(act.steps[0].description, '{"en-US": "Net pong matches won"}')

        self.assertEqual(act.steps[1].step_id, 'dg')
        self.assertEqual(act.steps[1].description, '{"en-US": "Strokes over par in disc golf at Liberty"}')
        
        self.assertEqual(act.steps[2].step_id, 'lunch')
        self.assertEqual(act.steps[2].description, '{"en-US": "Lunch having been eaten"}')

        #Check model choice values
        slist = ['pong', 'dg', 'lunch']
        dlist = ['{"en-US": "Net pong matches won"}','{"en-US": "Strokes over par in disc golf at Liberty"}','{"en-US": "Lunch having been eaten"}']
        self.do_actvity_definition_performance_model(defPK, slist, dlist)

    #Test activity with definition that is cmi.interaction and sequencing interactionType
    def test_activity_definition_cmiInteraction_sequencing(self):    
        act = Activity.Activity(json.dumps({'objectType': 'activity', 'id':'fool',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'sequencing','correctResponsesPattern': ['lou,tom,andy,aaron'],
                'choices':[{'id': 'lou', 'description': {'en-US':'Lou'}},{'id': 'tom','description':{'en-US': 'Tom'}},
                {'id':'andy', 'description':{'en-US':'Andy'}},{'id':'aaron', 'description':{'en-US':'Aaron'}}]}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'fool', 'Activity')
        self.do_activity_model(act.activity.id, 'fool', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'sequencing')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'sequencing')

        self.assertEqual(act.answers[0].answer, 'lou,tom,andy,aaron')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['lou,tom,andy,aaron'])

        #Test object step values
        self.assertEqual(act.choices[0].choice_id, 'lou')
        self.assertEqual(act.choices[0].description, '{"en-US": "Lou"}')

        self.assertEqual(act.choices[1].choice_id, 'tom')
        self.assertEqual(act.choices[1].description, '{"en-US": "Tom"}')
        
        self.assertEqual(act.choices[2].choice_id, 'andy')
        self.assertEqual(act.choices[2].description, '{"en-US": "Andy"}')

        self.assertEqual(act.choices[3].choice_id, 'aaron')
        self.assertEqual(act.choices[3].description, '{"en-US": "Aaron"}')

        #Check model choice values
        clist = ['lou', 'tom', 'andy', 'aaron']
        dlist = ['{"en-US": "Lou"}','{"en-US": "Tom"}','{"en-US": "Andy"}', '{"en-US": "Aaron"}']
        self.do_actvity_definition_choices_model(defPK, clist, dlist)

    #Test activity with definition that is cmi.interaction and numeric interactionType
    def test_activity_definition_cmiInteraction_numeric(self):

        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foom',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'numeric','correctResponsesPattern': ['4'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'foom', 'Activity')
        self.do_activity_model(act.activity.id, 'foom', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'numeric')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'numeric')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, '4')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['4'])

    #Test activity with definition that is cmi.interaction and other interactionType
    def test_activity_definition_cmiInteraction_other(self):

        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id': 'foon',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'other','correctResponsesPattern': ['(35.937432,-86.868896)'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'foon', 'Activity')
        self.do_activity_model(act.activity.id, 'foon', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'other')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'other')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, '(35.937432,-86.868896)')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['(35.937432,-86.868896)'])
