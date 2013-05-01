from django.test import TestCase
from lrs import models
import json
from lrs.exceptions import ParamError, InvalidXML
from lrs.objects import Activity
import pdb

class ActivityModelsTests(TestCase):        
    #Called on all activity django models to see if they were created with the correct fields    
    def do_activity_model(self,realid,act_id, objType):
        self.assertEqual(models.activity.objects.filter(id=realid)[0].objectType, objType)
        self.assertEqual(models.activity.objects.filter(id=realid)[0].activity_id, act_id)

    #Called on all activity django models with definitions to see if they were created with the correct 
    # fields
    def do_activity_definition_model(self, fk,course, intType, moreInfo=""):
        act_def = models.activity_definition.objects.filter(activity=fk)[0]
        self.assertEqual(act_def.activity_definition_type, course)
        self.assertEqual(act_def.interactionType, intType)
        self.assertEqual(act_def.moreInfo, moreInfo)

    # Called on all activity django models with extensions to see if they were created with the correct 
    # fields and values. All extensions are created with the same three values and keys
    def do_activity_definition_extensions_model(self, def_fk, key1, key2, key3, value1, value2, value3):
        #Create list comprehesions to easier assess keys and values
        ext_list = models.activity_definition(pk=def_fk).extensions.values_list()
        ext_keys = [ext[1] for ext in ext_list]
        ext_vals = [ext[2] for ext in ext_list]

        self.assertIn(key1, ext_keys)
        self.assertIn(key2, ext_keys)
        self.assertIn(key3, ext_keys)
        self.assertIn(value1, ext_vals)
        self.assertIn(value2, ext_vals)
        self.assertIn(value3, ext_vals)

    #Called on all activity django models with a correctResponsePattern because of cmi.interaction type
    def do_activity_definition_correctResponsePattern_model(self, rsp_fk, answers):
        rspAnswers = models.correctresponsespattern_answer.objects.values_list('answer',
                     flat=True).filter(correctresponsespattern=rsp_fk)
        
        for answer in answers:
            self.assertIn(answer,rspAnswers)

    #Called on all activity django models with choices because of sequence and choice interactionType
    def do_actvity_definition_choices_model(self, def_fk, clist, dlist):
        # Grab all lang map IDs in act def
        desc_lang_maps = models.activity_definition_choice.objects.values_list('description',
                flat=True).filter(activity_definition=def_fk)
        
        # Recreate lang map and add to list for check
        lang_map_list = []
        for desc in desc_lang_maps:
            d = models.LanguageMap.objects.get(id=desc)
            tup = (d.key, d.value)
            lang_map_list.append(tup)

        choices = models.activity_definition_choice.objects.values_list('choice_id',
                flat=True).filter(activity_definition=def_fk)
        
        for c in clist:
            self.assertIn(c,choices)

        for d in dlist:
            self.assertIn(d, lang_map_list)

    #Called on all activity django models with scale because of likert interactionType
    def do_actvity_definition_likert_model(self, def_fk, clist, dlist):

        desc_lang_maps = models.activity_definition_scale.objects.values_list('description',
                flat=True).filter(activity_definition=def_fk)

        # Recreate lang map and add to list for check
        lang_map_list = []
        for desc in desc_lang_maps:
            d = models.LanguageMap.objects.get(id=desc)
            tup = (d.key, d.value)
            lang_map_list.append(tup)
        
        choices = models.activity_definition_scale.objects.values_list('scale_id',
                flat=True).filter(activity_definition=def_fk)

        for c in clist:
            self.assertIn(c,choices)

        for d in dlist:
            self.assertIn(d, lang_map_list)

    #Called on all activity django models with steps because of performance interactionType
    def do_actvity_definition_performance_model(self, def_fk, slist, dlist):

        desc_lang_maps = models.activity_definition_step.objects.values_list('description',
                flat=True).filter(activity_definition=def_fk)

        # Recreate lang map and add to list for check
        lang_map_list = []
        for desc in desc_lang_maps:
            d = models.LanguageMap.objects.get(id=desc)
            tup = (d.key, d.value)
            lang_map_list.append(tup)        
        steps = models.activity_definition_step.objects.values_list('step_id',
            flat=True).filter(activity_definition=def_fk)
        
        for s in slist:
            self.assertIn(s,steps)

        for d in dlist:
            self.assertIn(d, lang_map_list)

    #Called on all activity django models with source and target because of matching interactionType
    def do_actvity_definition_matching_model(self, def_fk, source_id_list, source_desc_list,
                                             target_id_list, target_desc_list):

        source_desc_lang_maps = models.activity_definition_source.objects.values_list('description',
                flat=True).filter(activity_definition=def_fk)

        # Recreate lang map and add to list for check
        source_lang_map_list = []
        for desc in source_desc_lang_maps:
            d = models.LanguageMap.objects.get(id=desc)
            tup = (d.key, d.value)
            source_lang_map_list.append(tup)

        sources = models.activity_definition_source.objects.values_list('source_id',
                flat=True).filter(activity_definition=def_fk)
        

        target_desc_lang_maps = models.activity_definition_target.objects.values_list('description',
                flat=True).filter(activity_definition=def_fk)

        # Recreate lang map and add to list for check
        target_lang_map_list = []
        for desc in target_desc_lang_maps:
            d = models.LanguageMap.objects.get(id=desc)
            tup = (d.key, d.value)
            target_lang_map_list.append(tup)
        
        targets = models.activity_definition_target.objects.values_list('target_id',
                flat=True).filter(activity_definition=def_fk)
        
        for s_id in source_id_list:
            self.assertIn(s_id,sources)

        for s_desc in source_desc_list:
            self.assertIn(s_desc, source_lang_map_list)

        for t_id in target_id_list:
            self.assertIn(t_id,targets)

        for t_desc in target_desc_list:
            self.assertIn(t_desc, target_lang_map_list)            


    # Test activity that doesn't have a def (populates everything from JSON)
    def test_activity_no_def_json_conform(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity',
            'id': 'http://localhost:8000/XAPI/actexample/'}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()

        # Set not always returned in the same order
        for ns in name_set:
            if ns.key == 'en-FR':
                self.assertEqual(ns.value, 'Example Name')
            elif ns.key == 'en-CH':
                self.assertEqual(ns.value, 'Alt Name')

        for ds in desc_set:
            if ds.key == 'en-US':
                self.assertEqual(ds.value, 'Example Desc')
            elif ns.key == 'en-CH':
                self.assertEqual(ds.value, 'Alt Desc')

        self.do_activity_model(act.activity.id, 'http://localhost:8000/XAPI/actexample/', 'Activity')        
        self.do_activity_definition_model(fk, 'module','course')

    # Test that passing in the same info gets the same activity
    def test_activity_no_def_not_link_schema_conform1(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity',
            'id': 'http://localhost:8000/XAPI/actexample/'}))
        
        act2 = Activity.Activity(json.dumps({'objectType': 'Activity',
            'id': 'http://localhost:8000/XAPI/actexample/'}))

        self.assertEqual(act2.activity.id, act.activity.id)

    # Test activity that doesn't have a def with extensions (populates everything from XML)
    def test_activity_no_def_schema_conform_extensions(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity',
            'id': 'http://localhost:8000/XAPI/actexample2/'}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        
        self.assertEqual(name_set[0].key, 'en-US')
        self.assertEqual(name_set[0].value, 'Example Name')

        self.assertEqual(desc_set[0].key, 'en-US')
        self.assertEqual(desc_set[0].value, 'Example Desc')

        self.do_activity_model(act.activity.id, 'http://localhost:8000/XAPI/actexample2/', 'Activity')        
        self.do_activity_definition_model(fk, 'module','course')

        self.do_activity_definition_extensions_model(act_def, 'ext:keya', 'ext:keyb', 'ext:keyc','first value',
            'second value', 'third value')

    # Test an activity that has a def, and the provided ID doesn't resolve
    # (should still use values from JSON)
    def test_activity_no_resolve(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity',
                'id':'act://var/www/adllrs/activity/example.json','definition': {'name': {'en-CH':'testname'},
                'description': {'en-US':'testdesc'}, 'type': 'course','interactionType': 'intType'}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        
        self.assertEqual(name_set[0].key, 'en-CH')
        self.assertEqual(name_set[0].value, 'testname')

        self.assertEqual(desc_set[0].key, 'en-US')
        self.assertEqual(desc_set[0].value, 'testdesc')

        self.do_activity_model(act.activity.id, 'act://var/www/adllrs/activity/example.json', 'Activity')        
        self.do_activity_definition_model(fk, 'course', 'intType')

    # Test an activity that has a def (should use values from payload and override JSON from ID)
    def test_activity_from_id(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity',
                'id':'http://localhost:8000/XAPI/actexample4/','definition': {'name': {'en-FR': 'name'},
                'description': {'en-FR':'desc'}, 'type': 'course','interactionType': 'intType'}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()

        self.assertEqual(name_set[0].key, 'en-FR')
        self.assertEqual(name_set[0].value, 'name')

        self.assertEqual(desc_set[0].key, 'en-FR')
        self.assertEqual(desc_set[0].value, 'desc')

        self.do_activity_model(act.activity.id, 'http://localhost:8000/XAPI/actexample4/', 'Activity')        
        self.do_activity_definition_model(fk, 'course','intType')

    # Test an activity that has a def and the ID resolves (should use values from payload)
    def test_activity_id_resolve(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id': 'http://localhost:8000/XAPI/',
                'definition': {'name': {'en-GB':'testname'},'description': {'en-GB':'testdesc1'},
                'type': 'link','interactionType': 'intType'}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        
        self.assertEqual(name_set[0].key, 'en-GB')
        self.assertEqual(name_set[0].value, 'testname')

        self.assertEqual(desc_set[0].key, 'en-GB')
        self.assertEqual(desc_set[0].value, 'testdesc1')

        self.do_activity_model(act.activity.id, 'http://localhost:8000/XAPI/', 'Activity')        
        self.do_activity_definition_model(fk, 'link', 'intType')

    # Throws exception because incoming data is not JSON
    def test_activity_not_json(self):
        self.assertRaises(ParamError, Activity.Activity,
            "This string should throw exception since it's not JSON")

    #Test activity where given URL isn't URI
    def test_activity_invalid_activity_id(self):
        self.assertRaises(ParamError, Activity.Activity, json.dumps({'id': 'foo',
                'objectType':'Activity','definition': {'name': {'en-GB':'testname'},
                'description': {'en-GB':'testdesc'}, 'type': 'link','interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get,
                activity_id='foo')

    #Test activity with definition - must retrieve activity object in order to test definition from DB
    def test_activity_definition(self):
        act = Activity.Activity(json.dumps({'id':'act:fooc',
                'definition': {'name': {'en-GB':'testname'},'description': {'en-US':'testdesc'}, 
                'type': 'course','interactionType': 'intType'}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        
        self.assertEqual(name_set[0].key, 'en-GB')
        self.assertEqual(name_set[0].value, 'testname')

        self.assertEqual(desc_set[0].key, 'en-US')
        self.assertEqual(desc_set[0].value, 'testdesc')

        self.do_activity_model(act.activity.id,'act:fooc', 'Activity')        
        self.do_activity_definition_model(fk, 'course', 'intType')

    def test_activity_definition_with_url_field(self):
        act = Activity.Activity(json.dumps({'objectType': 'Wrong', 'id':'act:fooc',
                'definition': {'name': {'en-GB':'testname'},'description': {'en-US':'testdesc'}, 
                'type': 'course', 'moreInfo':'http://some/json/doc','interactionType': 'intType'}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-GB')
        self.assertEqual(name_set[0].value, 'testname')

        self.assertEqual(desc_set[0].key, 'en-US')
        self.assertEqual(desc_set[0].value, 'testdesc')

        self.do_activity_model(act.activity.id,'act:fooc', 'Activity')        
        self.do_activity_definition_model(fk, 'course', 'intType','http://some/json/doc')

    #Test activity with definition given wrong type (won't create it)
    def test_activity_definition_wrong_type(self):
        self.assertRaises(ParamError, Activity.Activity, json.dumps({'objectType': 'Activity',
                'id':'http://msn.com','definition': {'NAME': {'en-CH':'testname'},
                'descripTION': {'en-CH':'testdesc'}, 'tYpe': 'wrong','interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get,
            activity_id='http://msn.com')
    
    #Test activity with definition missing name in definition (won't create it)
    def test_activity_definition_required_fields(self):
        self.assertRaises(ParamError, Activity.Activity, json.dumps({'objectType': 'Activity',
                'id':'http://google.com','definition': {'description': {'en-CH':'testdesc'},
                'type': 'wrong','interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get,
            activity_id='http://google.com')

    # Test activity with definition that contains extensions - need to retrieve activity and activity definition objects
    # in order to test extenstions
    def test_activity_definition_extensions(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'act:food',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-CH':'testdesc2'},
                'type': 'course','interactionType': 'intType2', 'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2','ext:key3': 'value3'}}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-FR')
        self.assertEqual(name_set[0].value, 'testname2')

        self.assertEqual(desc_set[0].key, 'en-CH')
        self.assertEqual(desc_set[0].value, 'testdesc2')

        self.do_activity_model(act.activity.id,'act:food', 'Activity')        
        self.do_activity_definition_model(fk, 'course','intType2')

        self.do_activity_definition_extensions_model(act_def, 'ext:key1', 'ext:key2', 'ext:key3', 'value1', 'value2',
                'value3')

    def test_multiple_names_and_descs(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'act:food',
                'definition': {'name': {'en-FR':'testname2','en-US': 'testnameEN'},'description': {'en-CH':'testdesc2',
                'en-GB': 'testdescGB'},'type': 'course','interactionType': 'intType2', 'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2','ext:key3': 'value3'}}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        def_fk = models.activity_definition.objects.filter(activity=fk)

        name_set = def_fk[0].name.all()
        desc_set = def_fk[0].description.all()
        
        for ns in name_set:
            if ns.key == 'en-US':
                self.assertEqual(ns.value, 'testnameEN')
            elif ns.key == 'en-FR':
                self.assertEqual(ns.value, 'testname2')

        for ds in desc_set:
            if ds.key == 'en-GB':
                self.assertEqual(ds.value, 'testdescGB')
            elif ds.key == 'en-CH':
                self.assertEqual(ds.value, 'testdesc2')

        self.do_activity_model(act.activity.id,'act:food', 'Activity')        
        self.do_activity_definition_model(fk, 'course', 'intType2')

        self.do_activity_definition_extensions_model(def_fk, 'ext:key1', 'ext:key2', 'ext:key3', 'value1', 'value2',
                'value3')


    #Test activity with definition given wrong interactionType (won't create one)
    def test_activity_definition_wrong_interactionType(self):

        self.assertRaises(ParamError, Activity.Activity, json.dumps({'objectType': 'Activity', 
                'id':'http://facebook.com','definition': {'name': {'en-US':'testname2'},
                'description': {'en-GB':'testdesc2'}, 'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction',
                'interactionType': 'intType2', 'correctResponsesPatteRN': 'response',
                'extensions': {'ext:key1': 'value1', 'ext:key2': 'value2','ext:key3': 'value3'}}}))
     
        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get,
                          activity_id='http://facebook.com')

    #Test activity with definition and valid interactionType-it must also provide the
    # correctResponsesPattern field (wont' create it)
    def test_activity_definition_no_correctResponsesPattern(self):
        self.assertRaises(ParamError, Activity.Activity, json.dumps({'objectType': 'Activity',
                'id':'http://twitter.com','definition': {'name': {'en-US':'testname2'},
                'description': {'en-CH':'testdesc2'},'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction',
                'interactionType': 'true-false', 'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2','ext:key3': 'value3'}}}))
     
        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get,
                          activity_id='http://twitter.com')

    #Test activity with definition that is cmi.interaction and true-false interactionType
    def test_activity_definition_cmiInteraction_true_false(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'act:fooe',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-US':'testdesc2'}, 
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'true-false',
                'correctResponsesPattern': ['true'] ,'extensions': {'ext:key1': 'value1', 'ext:key2': 'value2',
                'ext:key3': 'value3'}}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-FR')
        self.assertEqual(name_set[0].value, 'testname2')

        self.assertEqual(desc_set[0].key, 'en-US')
        self.assertEqual(desc_set[0].value, 'testdesc2')        

        rsp_fk = models.activity_def_correctresponsespattern.objects.filter(activity_definition=act_def)

        self.do_activity_model(act.activity.id,'act:fooe', 'Activity')                
        self.do_activity_definition_model(fk, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','true-false')

        self.do_activity_definition_extensions_model(act_def, 'ext:key1', 'ext:key2', 'ext:key3', 'value1',
                                                    'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_model(rsp_fk, ['true'])
    
    #Test activity with definition that is cmi.interaction and multiple choice interactionType
    def test_activity_definition_cmiInteraction_multiple_choice(self):    
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'act:foof',
                'definition': {'name': {'en-US':'testname1'},'description': {'en-US':'testdesc1'},
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'choice',
                'correctResponsesPattern': ['golf', 'tetris'],'choices':[{'id': 'golf', 
                'description': {'en-US':'Golf Example', 'en-GB': 'GOLF'}},{'id': 'tetris',
                'description':{'en-US': 'Tetris Example', 'en-GB': 'TETRIS'}}, {'id':'facebook', 
                'description':{'en-US':'Facebook App', 'en-GB': 'FACEBOOK'}},{'id':'scrabble', 
                'description': {'en-US': 'Scrabble Example', 'en-GB': 'SCRABBLE'}}],'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2','ext:key3': 'value3'}}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-US')
        self.assertEqual(name_set[0].value, 'testname1')

        self.assertEqual(desc_set[0].key, 'en-US')
        self.assertEqual(desc_set[0].value, 'testdesc1')

        rsp_fk = models.activity_def_correctresponsespattern.objects.filter(activity_definition=act_def)

        self.do_activity_model(act.activity.id,'act:foof', 'Activity')
        self.do_activity_definition_model(fk, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'choice')

        self.do_activity_definition_extensions_model(act_def, 'ext:key1', 'ext:key2', 'ext:key3', 'value1', 'value2',
                                                     'value3')

        self.do_activity_definition_correctResponsePattern_model(rsp_fk, ['golf', 'tetris'])
        
        #Check model choice values
        clist = ['golf', 'tetris', 'facebook', 'scrabble']
        dlist = [("en-US","Golf Example"),("en-US", "Tetris Example"),("en-US", "Facebook App"),
                 ("en-US", "Scrabble Example"), ('en-GB','GOLF'), ('en-GB', 'TETRIS'), ('en-GB', 'FACEBOOK'),
                 ('en-GB', 'SCRABBLE')]

        self.do_actvity_definition_choices_model(act_def, clist, dlist)        
        
    #Test activity with definition that is cmi.interaction and multiple choice but missing choices (won't create it)
    def test_activity_definition_cmiInteraction_multiple_choice_no_choices(self):
        self.assertRaises(ParamError, Activity.Activity, json.dumps({'objectType': 'Activity', 
                'id':'http://wikipedia.org','definition': {'name': {'en-US':'testname2'},
                'description': {'en-US':'testdesc2'},'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction',
                'interactionType': 'choice','correctResponsesPattern': ['golf', 'tetris'],
                'extensions': {'ext:key1': 'value1', 'ext:key2': 'value2','ext:key3': 'value3'}}}))   

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get,
                activity_id='http://wikipedia.org')
    
    #Test activity with definition that is cmi.interaction and fill in interactionType
    def test_activity_definition_cmiInteraction_fill_in(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'act:foog',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'fill-in',
                'correctResponsesPattern': ['Fill in answer'],'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2', 'ext:key3': 'value3'}}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-FR')
        self.assertEqual(name_set[0].value, 'testname2')

        self.assertEqual(desc_set[0].key, 'en-FR')
        self.assertEqual(desc_set[0].value, 'testdesc2')

        rsp_fk = models.activity_def_correctresponsespattern.objects.filter(activity_definition=act_def)

        self.do_activity_model(act.activity.id,'act:foog', 'Activity')

        self.do_activity_definition_model(fk, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','fill-in')

        self.do_activity_definition_extensions_model(act_def, 'ext:key1', 'ext:key2', 'ext:key3', 'value1', 'value2',
                                                    'value3')

        self.do_activity_definition_correctResponsePattern_model(rsp_fk, ['Fill in answer'])

    #Test activity with definition that is cmi.interaction and long fill in interactionType
    def test_activity_definition_cmiInteraction_long_fill_in(self):

        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'act:fooh',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'fill-in',
                'correctResponsesPattern': ['Long fill in answer'],'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2','ext:key3': 'value3'}}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-FR')
        self.assertEqual(name_set[0].value, 'testname2')

        self.assertEqual(desc_set[0].key, 'en-FR')
        self.assertEqual(desc_set[0].value, 'testdesc2')

        rsp_fk = models.activity_def_correctresponsespattern.objects.filter(activity_definition=act_def)

        self.do_activity_model(act.activity.id, 'act:fooh', 'Activity')

        self.do_activity_definition_model(fk, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','fill-in')

        self.do_activity_definition_extensions_model(act_def, 'ext:key1', 'ext:key2', 'ext:key3', 'value1', 'value2',
                                                     'value3')

        self.do_activity_definition_correctResponsePattern_model(rsp_fk, ['Long fill in answer'])

    #Test activity with definition that is cmi.interaction and likert interactionType
    def test_activity_definition_cmiInteraction_likert(self):    
        act = Activity.Activity(json.dumps({'objectType': 'Still gonna be activity', 'id':'act:fooi',
                'definition': {'name': {'en-CH':'testname2'},'description': {'en-CH':'testdesc2'},
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'likert',
                'correctResponsesPattern': ['likert_3'],'scale':[{'id': 'likert_0',
                'description': {'en-US':'Its OK', 'en-GB': 'Tis OK'}},{'id': 'likert_1',
                'description':{'en-US': 'Its Pretty Cool', 'en-GB':'Tis Pretty Cool'}}, {'id':'likert_2',
                'description':{'en-US':'Its Cool Cool', 'en-GB':'Tis Cool Cool'}},
                {'id':'likert_3', 'description': {'en-US': 'Its Gonna Change the World'}}]}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-CH')
        self.assertEqual(name_set[0].value, 'testname2')

        self.assertEqual(desc_set[0].key, 'en-CH')
        self.assertEqual(desc_set[0].value, 'testdesc2')

        rsp_fk = models.activity_def_correctresponsespattern.objects.filter(activity_definition=act_def)

        self.do_activity_model(act.activity.id, 'act:fooi', 'Activity')

        self.do_activity_definition_model(fk, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'likert')

        self.do_activity_definition_correctResponsePattern_model(rsp_fk, ['likert_3'])

        #Check model choice values
        clist = ['likert_0', 'likert_1', 'likert_2', 'likert_3']
        dlist = [("en-US", "Its OK"),("en-US", "Its Pretty Cool"), ("en-US", "Its Cool Cool"),
                 ("en-US", "Its Gonna Change the World"), ('en-GB', 'Tis OK'), ('en-GB', 'Tis Pretty Cool'),
                 ('en-GB', 'Tis Cool Cool')]
        
        self.do_actvity_definition_likert_model(act_def, clist, dlist)

    #Test activity with definition that is cmi.interaction and matching interactionType
    def test_activity_definition_cmiInteraction_matching(self):    
        act = Activity.Activity(json.dumps({'objectType': 'Still gonna be activity', 'id':'act:fooj',
                'definition': {'name': {'en-CH':'testname2'},'description': {'en-CH':'testdesc2'},
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'matching',
                'correctResponsesPattern': ['lou.3,tom.2,andy.1'],'source':[{'id': 'lou',
                'description': {'en-US':'Lou', 'it': 'Luigi'}},{'id': 'tom','description':{'en-US': 'Tom', 'it':'Tim'}},
                {'id':'andy', 'description':{'en-US':'Andy'}}],'target':[{'id':'1',
                'description':{'en-US': 'SCORM Engine'}},{'id':'2','description':{'en-US': 'Pure-sewage'}},
                {'id':'3', 'description':{'en-US': 'SCORM Cloud', 'en-CH': 'cloud'}}]}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-CH')
        self.assertEqual(name_set[0].value, 'testname2')

        self.assertEqual(desc_set[0].key, 'en-CH')
        self.assertEqual(desc_set[0].value, 'testdesc2')

        rsp_fk = models.activity_def_correctresponsespattern.objects.filter(activity_definition=act_def)

        self.do_activity_model(act.activity.id, 'act:fooj', 'Activity')

        self.do_activity_definition_model(fk, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'matching')

        self.do_activity_definition_correctResponsePattern_model(rsp_fk, ['lou.3,tom.2,andy.1'])

        #Check model choice values
        source_id_list = ['lou', 'tom', 'andy']
        source_desc_list = [("en-US", "Lou"),("en-US", "Tom"),("en-US", "Andy"),('it', 'Luigi'), ('it', 'Tim')]
        target_id_list = ['1','2','3']
        target_desc_list = [("en-US", "SCORM Engine"),("en-US", "Pure-sewage"),
                            ("en-US", "SCORM Cloud"), ('en-CH', 'cloud') ]

        self.do_actvity_definition_matching_model(act_def, source_id_list, source_desc_list,
                                                  target_id_list, target_desc_list)

    #Test activity with definition that is cmi.interaction and performance interactionType
    def test_activity_definition_cmiInteraction_performance(self):    
        act = Activity.Activity(json.dumps({'objectType': 'activity', 'id':'act:fook',
                'definition': {'name': {'en-us':'testname2'},'description': {'en-us':'testdesc2'},
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'performance',
                'correctResponsesPattern': ['pong.1,dg.10,lunch.4'],'steps':[{'id': 'pong',
                'description': {'en-US':'Net pong matches won', 'en-GB': 'won'}},{'id': 'dg',
                'description':{'en-US': 'Strokes over par in disc golf at Liberty'}},
                {'id':'lunch', 'description':{'en-US':'Lunch having been eaten'}}]}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-us')
        self.assertEqual(name_set[0].value, 'testname2')

        self.assertEqual(desc_set[0].key, 'en-us')
        self.assertEqual(desc_set[0].value, 'testdesc2')        
        rsp_fk = models.activity_def_correctresponsespattern.objects.filter(activity_definition=act_def)

        self.do_activity_model(act.activity.id, 'act:fook', 'Activity')

        self.do_activity_definition_model(fk, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'performance')

        self.do_activity_definition_correctResponsePattern_model(rsp_fk, ['pong.1,dg.10,lunch.4'])

        #Check model choice values
        slist = ['pong', 'dg', 'lunch']
        dlist = [("en-US", "Net pong matches won"),("en-US", "Strokes over par in disc golf at Liberty"),
                 ("en-US", "Lunch having been eaten"), ('en-GB', 'won')]
        
        self.do_actvity_definition_performance_model(act_def, slist, dlist)

    # Test activity with definition that is cmi.interaction and sequencing interactionType
    def test_activity_definition_cmiInteraction_sequencing(self):    
        act = Activity.Activity(json.dumps({'objectType': 'activity', 'id':'act:fool',
                'definition': {'name': {'en-GB':'testname2'},'description': {'en-GB':'testdesc2'},
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'sequencing',
                'correctResponsesPattern': ['lou,tom,andy,aaron'],'choices':[{'id': 'lou',
                'description': {'en-US':'Lou'}},{'id': 'tom','description':{'en-US': 'Tom'}},
                {'id':'andy', 'description':{'en-US':'Andy'}},{'id':'aaron',
                'description':{'en-US':'Aaron', 'en-GB': 'Erin'}}]}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-GB')
        self.assertEqual(name_set[0].value, 'testname2')

        self.assertEqual(desc_set[0].key, 'en-GB')
        self.assertEqual(desc_set[0].value, 'testdesc2')

        rsp_fk = models.activity_def_correctresponsespattern.objects.filter(activity_definition=act_def)

        self.do_activity_model(act.activity.id, 'act:fool', 'Activity')

        self.do_activity_definition_model(fk, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'sequencing')

        self.do_activity_definition_correctResponsePattern_model(rsp_fk, ['lou,tom,andy,aaron'])
        #Check model choice values
        clist = ['lou', 'tom', 'andy', 'aaron']
        dlist = [("en-US", "Lou"),("en-US", "Tom"),("en-US", "Andy"), ("en-US", "Aaron"), ('en-GB', 'Erin')]
        self.do_actvity_definition_choices_model(act_def, clist, dlist)

    #Test activity with definition that is cmi.interaction and numeric interactionType
    def test_activity_definition_cmiInteraction_numeric(self):

        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'act:foom',
                'definition': {'name': {'en-CH':'testname2'},'description': {'en-CH':'testdesc2'},
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'numeric','correctResponsesPattern': ['4'],
                'extensions': {'ext:key1': 'value1', 'ext:key2': 'value2','ext:key3': 'value3'}}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-CH')
        self.assertEqual(name_set[0].value, 'testname2')

        self.assertEqual(desc_set[0].key, 'en-CH')
        self.assertEqual(desc_set[0].value, 'testdesc2')

        rsp_fk = models.activity_def_correctresponsespattern.objects.filter(activity_definition=act_def)

        self.do_activity_model(act.activity.id, 'act:foom', 'Activity')

        self.do_activity_definition_model(fk, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'numeric')

        self.do_activity_definition_extensions_model(act_def, 'ext:key1', 'ext:key2', 'ext:key3', 'value1', 'value2',
                                                     'value3')

        self.do_activity_definition_correctResponsePattern_model(rsp_fk, ['4'])

    #Test activity with definition that is cmi.interaction and other interactionType
    def test_activity_definition_cmiInteraction_other(self):

        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id': 'act:foon',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'other',
                'correctResponsesPattern': ['(35.937432,-86.868896)'],'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2','ext:key3': 'value3'}}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-FR')
        self.assertEqual(name_set[0].value, 'testname2')

        self.assertEqual(desc_set[0].key, 'en-FR')
        self.assertEqual(desc_set[0].value, 'testdesc2')

        rsp_fk = models.activity_def_correctresponsespattern.objects.filter(activity_definition=act_def)

        self.do_activity_model(act.activity.id, 'act:foon', 'Activity')

        self.do_activity_definition_model(fk, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'other')

        self.do_activity_definition_extensions_model(act_def, 'ext:key1', 'ext:key2', 'ext:key3', 'value1', 'value2',
                                                     'value3')

        self.do_activity_definition_correctResponsePattern_model(rsp_fk, ['(35.937432,-86.868896)'])

    # Should be the same, no auth required
    def test_multiple_activities(self):
        act1 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foob'}))
        act2 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foob'}))
        act3 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foob'}))
        act4 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foon'}))

        self.assertEqual(act1.activity.id, act2.activity.id)
        self.assertEqual(act1.activity.id, act3.activity.id)
        self.assertEqual(act2.activity.id, act3.activity.id)
        self.assertNotEqual(act1.activity.id, act4.activity.id)

    def test_language_map_description_name(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id': 'act:foz',
                'definition': {'name': {'en-US':'actname'},'description': {'en-us':'actdesc'},
                'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'other',
                    'correctResponsesPattern': ['(35,-86)']}}))

        fk = models.activity.objects.filter(id=act.activity.id)
        act_def = models.activity_definition.objects.filter(activity=fk)

        name_set = act_def[0].name.all()
        desc_set = act_def[0].description.all()
        

        self.assertEqual(name_set[0].key, 'en-US')
        self.assertEqual(name_set[0].value, 'actname')

        self.assertEqual(desc_set[0].key, 'en-us')
        self.assertEqual(desc_set[0].value, 'actdesc')
        self.do_activity_model(act.activity.id, 'act:foz', 'Activity')

        self.do_activity_definition_model(fk, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'other')

    def test_multiple_activities_update_name(self):
        act1 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-US':'actname'},'description': {'en-us':'actdesc'}, 
            'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}))
        
        act2 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-US':'actname2'},'description': {'en-us':'actdesc'}, 
            'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}))

        fk1 = models.activity.objects.filter(id=act1.activity.id)[0]
        self.do_activity_model(act1.activity.id, 'act:foob', 'Activity')
        act_def1 = models.activity_definition.objects.filter(activity=fk1)

        name_set1 = act_def1[0].name.all()
        desc_set1 = act_def1[0].description.all()
        

        self.assertEqual(name_set1[0].key, 'en-US')
        self.assertEqual(name_set1[0].value, 'actname2')

        self.assertEqual(desc_set1[0].key, 'en-us')
        self.assertEqual(desc_set1[0].value, 'actdesc')        


        self.do_activity_definition_model(fk1, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'other')

        fk2 = models.activity.objects.filter(id=act2.activity.id)[0]
        self.do_activity_model(act2.activity.id, 'act:foob', 'Activity')
        act_def2 = models.activity_definition.objects.filter(activity=fk2)

        name_set2 = act_def2[0].name.all()
        desc_set2 = act_def2[0].description.all()
        

        self.assertEqual(name_set2[0].key, 'en-US')
        self.assertEqual(name_set2[0].value, 'actname2')

        self.assertEqual(desc_set2[0].key, 'en-us')
        self.assertEqual(desc_set2[0].value, 'actdesc')        
        self.do_activity_definition_model(fk2, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'other')

        self.assertEqual(act1.activity, act2.activity)
        self.assertEqual(fk1.activity_definition, fk2.activity_definition)

        # __contains makes the filter case sensitive
        self.assertEqual(len(models.name_lang.objects.filter(key__contains = 'en-US')), 1)

        # Should have one desc
        self.assertEqual(len(models.desc_lang.objects.all()), 1)
        
    def test_multiple_activities_update_desc(self):
        act1 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foobe',
            'definition':{'name': {'en-US':'actname'},'description': {'en-us':'actdesc'}, 
            'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}))
        
        act2 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foobe',
            'definition':{'name': {'en-US':'actname'},'description': {'en-us':'actdesc2'}, 
            'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}))

        fk1 = models.activity.objects.filter(id=act1.activity.id)[0]
        self.do_activity_model(act1.activity.id, 'act:foobe', 'Activity')
        act_def1 = models.activity_definition.objects.get(activity=fk1)

        name_set1 = act_def1.name.all()
        desc_set1 = act_def1.description.all()
        

        self.assertEqual(name_set1[0].key, 'en-US')
        self.assertEqual(name_set1[0].value, 'actname')

        self.assertEqual(desc_set1[0].key, 'en-us')
        self.assertEqual(desc_set1[0].value, 'actdesc2')        
        self.do_activity_definition_model(fk1, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'other')

        fk2 = models.activity.objects.filter(id=act2.activity.id)[0]
        self.do_activity_model(act2.activity.id, 'act:foobe', 'Activity')
        act_def2 = models.activity_definition.objects.get(activity=fk2)

        name_set2 = act_def2.name.all()
        desc_set2 = act_def2.description.all()
        
        self.assertEqual(name_set2[0].key, 'en-US')
        self.assertEqual(name_set2[0].value, 'actname')

        self.assertEqual(desc_set2[0].key, 'en-us')
        self.assertEqual(desc_set2[0].value, 'actdesc2')        
        self.do_activity_definition_model(fk2, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'other')

        self.do_activity_definition_model(fk2, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'other')

        self.assertEqual(act1.activity, act2.activity)
        self.assertEqual(fk1.activity_definition, fk2.activity_definition)

        # __contains makes the filter case sensitive, no models with en-US should be stored
        self.assertEqual(len(models.name_lang.objects.filter(key__contains = 'en-US')), 1)

        # Should have 1 desc
        self.assertEqual(len(models.desc_lang.objects.all()), 1)

    def test_multiple_activities_update_both(self):
        act1 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname'},'description': {'en-FR':'actdesc'}, 
            'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}))
        
        act2 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname2'},'description': {'en-FR':'actdesc2'}, 
            'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}))

        fk1 = models.activity.objects.filter(id=act1.activity.id)[0]
        self.do_activity_model(act1.activity.id, 'act:foob', 'Activity')
        act_def1 = models.activity_definition.objects.filter(activity=fk1)

        name_set1 = act_def1[0].name.all()
        desc_set1 = act_def1[0].description.all()
        

        self.assertEqual(name_set1[0].key, 'en-CH')
        self.assertEqual(name_set1[0].value, 'actname2')

        self.assertEqual(desc_set1[0].key, 'en-FR')
        self.assertEqual(desc_set1[0].value, 'actdesc2')

        self.do_activity_definition_model(fk1, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'other')

        fk2 = models.activity.objects.filter(id=act2.activity.id)[0]
        self.do_activity_model(act2.activity.id, 'act:foob', 'Activity')
        act_def2 = models.activity_definition.objects.filter(activity=fk2)

        name_set2 = act_def2[0].name.all()
        desc_set2 = act_def2[0].description.all()
        

        self.assertEqual(name_set2[0].key, 'en-CH')
        self.assertEqual(name_set2[0].value, 'actname2')

        self.assertEqual(desc_set2[0].key, 'en-FR')
        self.assertEqual(desc_set2[0].value, 'actdesc2')         
        self.do_activity_definition_model(fk2,'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'other')

        self.assertEqual(act1.activity, act2.activity)
        self.assertEqual(fk1.activity_definition, fk2.activity_definition)

        # __contains makes the filter case sensitive, no models with en-US should be stored
        self.assertEqual(len(models.name_lang.objects.filter(key__contains = 'en-US')), 0)
        
        # Should have 1 desc
        self.assertEqual(len(models.desc_lang.objects.all()), 1)

    def test_multiple_activities_update_both_and_add(self):
        act1 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname'},'description': {'en-FR':'actdesc'}, 
            'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}))
        
        act2 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname2', 'en-US': 'altname'},'description': {'en-FR':'actdesc2', 'en-GB': 'altdesc'}, 
            'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}))

        fk1 = models.activity.objects.filter(id=act1.activity.id)[0]
        self.do_activity_model(act1.activity.id, 'act:foob', 'Activity')
        act_def1 = models.activity_definition.objects.filter(activity=fk1)

        name_set1 = act_def1[0].name.all()
        desc_set1 = act_def1[0].description.all()
        
        for ns in name_set1:
            if ns.key == 'en-CH':
                self.assertEqual(ns.value, 'actname2')
            elif ns.key == 'en-US':
                self.assertEqual(ns.value, 'altname')

        for ds in desc_set1:
            if ds.key == 'en-FR':
                self.assertEqual(ds.value, 'actdesc2')
            elif ds.key == 'en-GB':
                self.assertEqual(ds.value, 'altdesc')

        self.do_activity_definition_model(fk1, 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'other')

        fk2 = models.activity.objects.filter(id=act2.activity.id)[0]
        self.do_activity_model(act2.activity.id, 'act:foob', 'Activity')
        act_def2 = models.activity_definition.objects.filter(activity=fk2)

        name_set2 = act_def2[0].name.all()
        desc_set2 = act_def2[0].description.all()
        
        for ns in name_set2:
            if ns.key == 'en-CH':
                self.assertEqual(ns.value, 'actname2')
            elif ns.key == 'en-US':
                self.assertEqual(ns.value, 'altname')

        for ds in desc_set2:
            if ds.key == 'en-FR':
                self.assertEqual(ds.value, 'actdesc2')
            elif ns.key == 'en-GB':
                self.assertEqual(ds.value, 'altdesc')

        self.do_activity_definition_model(fk2,'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction', 'other')

        self.assertEqual(act1.activity, act2.activity)
        self.assertEqual(fk1.activity_definition, fk2.activity_definition)

        # __contains makes the filter case sensitive
        self.assertEqual(len(models.name_lang.objects.filter(key__contains = 'en-US')), 1)
        
        # Should have 2 descs
        self.assertEqual(len(models.desc_lang.objects.all()), 2)
        
    def test_del_act(self):
        act1 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname'},'description': {'en-FR':'actdesc'}, 
            'type': 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction','interactionType': 'other',
            'correctResponsesPattern': ['(35,-86)']}}))

        the_act = models.activity.objects.all()[0]
        the_def = the_act.activity_definition

        self.assertEqual(act1.activity.id, the_act.id)
        self.assertEqual(1, len(models.activity.objects.all()))
        self.assertEqual(1, len(models.activity_definition.objects.all()))
        self.assertEqual(1, len(models.name_lang.objects.all()))
        self.assertEqual(1, len(models.desc_lang.objects.all()))
        self.assertEqual(1, len(models.name_lang.objects.all()))
        self.assertEqual(1, len(models.activity_def_correctresponsespattern.objects.all()))

        the_act.delete()

        self.assertEqual(act1.activity.id, the_act.id)
        self.assertEqual(0, len(models.activity.objects.all()))
        self.assertEqual(0, len(models.activity_definition.objects.all()))
        self.assertEqual(0, len(models.name_lang.objects.all()))
        self.assertEqual(0, len(models.desc_lang.objects.all()))
        self.assertEqual(0, len(models.name_lang.objects.all()))
        self.assertEqual(0, len(models.activity_def_correctresponsespattern.objects.all()))
