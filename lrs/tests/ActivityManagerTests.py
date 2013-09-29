import base64
import json
from django.test import TestCase
from lrs import models, views
from django.core.urlresolvers import reverse
from django.conf import settings

class ActivityManagerTests(TestCase):
    @classmethod
    def setUpClass(cls):
        print "\n%s" % __name__

    def setUp(self):
        if not settings.HTTP_AUTH_ENABLED:
            settings.HTTP_AUTH_ENABLED = True
        
        self.username = "tester1"
        self.email = "test1@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {"username":self.username, "email":self.email,"password":self.password,"password2":self.password}
        response = self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0.0")

        if settings.HTTP_AUTH_ENABLED:
            response = self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0.0")           

    #Called on all activity django models to see if they were created with the correct fields    
    def do_activity_model(self,realid,act_id, objType):
        self.assertEqual(models.Activity.objects.filter(id=realid)[0].objectType, objType)
        self.assertEqual(models.Activity.objects.filter(id=realid)[0].activity_id, act_id)

    #Called on all activity django models with definitions to see if they were created with the correct 
    # fields
    def do_activity_definition_model(self, act, course, intType, moreInfo=""):
        self.assertEqual(act.activity_definition_type, course)
        self.assertEqual(act.activity_definition_interactionType, intType)
        self.assertEqual(act.activity_definition_moreInfo, moreInfo)

    # Called on all activity django models with extensions to see if they were created with the correct 
    # fields and values. All extensions are created with the same three values and keys
    def do_activity_definition_extensions_model(self, act, key1, key2, key3, value1, value2, value3):
        #Create list comprehesions to easier assess keys and values
        ext_keys = act.activity_definition_extensions.keys()
        ext_vals = act.activity_definition_extensions.values()

        self.assertIn(key1, ext_keys)
        self.assertIn(key2, ext_keys)
        self.assertIn(key3, ext_keys)
        self.assertIn(value1, ext_vals)
        self.assertIn(value2, ext_vals)
        self.assertIn(value3, ext_vals)

    #Called on all activity django models with a correctResponsePattern because of http://adlnet.gov/expapi/activities/cmi.interaction type
    def do_activity_definition_correctResponsePattern_model(self, act, answers):        
        for answer in answers:
            self.assertIn(answer,act.activity_definition_crpanswers)

    #Called on all activity django models with choices because of sequence and choice interactionType
    def do_actvity_definition_choices_model(self, act, clist, dlist):
        # Grab all lang map IDs in act def
        choice_ids = [v['id'] for v in act.activity_definition_choices]
        choice_descs = [v['description'] for v in act.activity_definition_choices]
        
        for c in clist:
            self.assertIn(c,choice_ids)

        for d in dlist:
            self.assertIn(d, choice_descs)

    #Called on all activity django models with scale because of likert interactionType
    def do_actvity_definition_likert_model(self, act, clist, dlist):
        scale_ids = [v['id'] for v in act.activity_definition_scales]        
        scale_descs = [v['description'] for v in act.activity_definition_scales]

        for c in clist:
            self.assertIn(c,scale_ids)

        for d in dlist:
            self.assertIn(d, scale_descs)

    #Called on all activity django models with steps because of performance interactionType
    def do_actvity_definition_performance_model(self, act, slist, dlist):
        step_ids = [v['id'] for v in act.activity_definition_steps]
        step_descs = [v['description'] for v in act.activity_definition_steps]

        for s in slist:
            self.assertIn(s,step_ids)

        for d in dlist:
            self.assertIn(d, step_descs)

    #Called on all activity django models with source and target because of matching interactionType
    def do_actvity_definition_matching_model(self, act, source_id_list, source_desc_list,
                                             target_id_list, target_desc_list):

        source_ids = [v['id'] for v in act.activity_definition_sources]
        source_descs = [v['description'] for v in act.activity_definition_sources]
        
        target_ids = [v['id'] for v in act.activity_definition_targets]
        target_descs = [v['description'] for v in act.activity_definition_targets]

        for s_id in source_id_list:
            self.assertIn(s_id,source_ids)

        for s_desc in source_desc_list:
            self.assertIn(s_desc, source_descs)

        for t_id in target_id_list:
            self.assertIn(t_id,target_ids)

        for t_desc in target_desc_list:
            self.assertIn(t_desc, target_descs)            


    # Test activity that doesn't have a def (populates everything from JSON)
    def test_activity_no_def_json_conform(self):
        stmt = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'http://localhost:8000/XAPI/actexample/'}})
        response = self.client.post(reverse(views.statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)
        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-FR')
        self.assertEqual(name_set.values()[0], 'Example Name')
        self.assertEqual(name_set.keys()[1], 'en-CH')
        self.assertEqual(name_set.values()[1], 'Alt Name')

        self.assertEqual(desc_set.keys()[0], 'en-US')
        self.assertEqual(desc_set.values()[0], 'Example Desc')
        self.assertEqual(desc_set.keys()[1], 'en-CH')
        self.assertEqual(desc_set.values()[1], 'Alt Desc')

        self.do_activity_model(act.id, 'http://localhost:8000/XAPI/actexample/', 'Activity')        
        self.do_activity_definition_model(act, 'type:module','course')

    # Test that passing in the same info gets the same activity
    def test_activity_no_def_not_link_schema_conform1(self):
        st_list = []

        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'http://localhost:8000/XAPI/actexample/'}})
        
        stmt2 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'http://localhost:8000/XAPI/actexample/'}})

        st_list.append(stmt1)
        st_list.append(stmt2)

        response = self.client.post(reverse(views.statements), st_list, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_ids = json.loads(response.content)
        st1 = models.Statement.objects.get(statement_id=st_ids[0])
        st2 = models.Statement.objects.get(statement_id=st_ids[1])
        act1 = models.Activity.objects.get(id=st1.object_activity.id)
        act2 = models.Activity.objects.get(id=st2.object_activity.id)
        self.assertEqual(act2.id, act1.id)

    # Test activity that doesn't have a def with extensions (populates everything from XML)
    def test_activity_no_def_schema_conform_extensions(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'http://localhost:8000/XAPI/actexample2/'}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description
        
        self.assertEqual(name_set.keys()[0], 'en-US')
        self.assertEqual(name_set.values()[0], 'Example Name')

        self.assertEqual(desc_set.keys()[0], 'en-US')
        self.assertEqual(desc_set.values()[0], 'Example Desc')

        self.do_activity_model(act.id, 'http://localhost:8000/XAPI/actexample2/', 'Activity')        
        self.do_activity_definition_model(act, 'type:module','course')

        self.do_activity_definition_extensions_model(act, 'ext:keya', 'ext:keyb', 'ext:keyc','first value',
            'second value', 'third value')

    # Test an activity that has a def, and the provided ID doesn't resolve
    # (should still use values from JSON)
    def test_activity_no_resolve(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity',
            'id':'act://var/www/adllrs/activity/example.json','definition': {'name': {'en-CH':'testname'},
            'description': {'en-US':'testdesc'}, 'type': 'type:course','interactionType': 'other'}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-CH')
        self.assertEqual(name_set.values()[0], 'testname')

        self.assertEqual(desc_set.keys()[0], 'en-US')
        self.assertEqual(desc_set.values()[0], 'testdesc')

        self.do_activity_model(act.id, 'act://var/www/adllrs/activity/example.json', 'Activity')        
        self.do_activity_definition_model(act, 'type:course', 'other')

    # Test an activity that has a def (should use values from payload and override JSON from ID)
    def test_activity_from_id(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity',
                'id':'http://localhost:8000/XAPI/actexample4/','definition': {'name': {'en-FR': 'name'},
                'description': {'en-FR':'desc'}, 'type': 'type:course','interactionType': 'other'}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)[0]
        st = models.Statement.objects.get(statement_id=st_id)
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-FR')
        self.assertEqual(name_set.values()[0], 'name')

        self.assertEqual(desc_set.keys()[0], 'en-FR')
        self.assertEqual(desc_set.values()[0], 'desc')

        self.do_activity_model(act.id, 'http://localhost:8000/XAPI/actexample4/', 'Activity')        
        self.do_activity_definition_model(act, 'type:course','other')

    # Test an activity that has a def and the ID resolves (should use values from payload)
    def test_activity_id_resolve(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id': 'http://localhost:8000/XAPI/',
                'definition': {'name': {'en-GB':'testname'},'description': {'en-GB':'testdesc1'},
                'type': 'type:link','interactionType': 'other'}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description
        
        self.assertEqual(name_set.keys()[0], 'en-GB')
        self.assertEqual(name_set.values()[0], 'testname')

        self.assertEqual(desc_set.keys()[0], 'en-GB')
        self.assertEqual(desc_set.values()[0], 'testdesc1')

        self.do_activity_model(act.id, 'http://localhost:8000/XAPI/', 'Activity')        
        self.do_activity_definition_model(act, 'type:link', 'other')

    # Throws exception because incoming data is not JSON
    def test_activity_not_json(self):
        stmt1 = "This string should throw exception since it's not JSON"

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, "Cannot evaluate data into dictionary to parse -- Error:  in This string should throw exception since it's not JSON")

    #Test activity where given URL isn't URI
    def test_activity_invalid_activity_id(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'id': 'foo',
                'objectType':'Activity','definition': {'name': {'en-GB':'testname'},
                'description': {'en-GB':'testdesc'}, 'type': 'type:link','interactionType': 'other'}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Activity id with value foo was not a valid URI')

    #Test activity with definition - must retrieve activity object in order to test definition from DB
    def test_activity_definition(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'id':'act:fooc',
                'definition': {'name': {'en-GB':'testname'},'description': {'en-US':'testdesc'}, 
                'type': 'type:course','interactionType': 'other'}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")       
        self.assertEqual(response.status_code, 200)

        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description
        
        self.assertEqual(name_set.keys()[0], 'en-GB')
        self.assertEqual(name_set.values()[0], 'testname')

        self.assertEqual(desc_set.keys()[0], 'en-US')
        self.assertEqual(desc_set.values()[0], 'testdesc')

        self.do_activity_model(act.id,'act:fooc', 'Activity')        
        self.do_activity_definition_model(act, 'type:course', 'other')

    # Test activity with definition that contains extensions - need to retrieve activity and activity definition objects
    # in order to test extenstions
    def test_activity_definition_extensions(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id':'act:food',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-CH':'testdesc2'},
                'type': 'type:course','interactionType': 'other', 'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2','ext:key3': 'value3'}}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-FR')
        self.assertEqual(name_set.values()[0], 'testname2')

        self.assertEqual(desc_set.keys()[0], 'en-CH')
        self.assertEqual(desc_set.values()[0], 'testdesc2')

        self.do_activity_model(act.id,'act:food', 'Activity')        
        self.do_activity_definition_model(act, 'type:course','other')

        self.do_activity_definition_extensions_model(act, 'ext:key1', 'ext:key2', 'ext:key3',
            'value1', 'value2', 'value3')

    def test_multiple_names_and_descs(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id':'act:food',
                'definition': {'name': {'en-FR':'testname2','en-US': 'testnameEN'},'description': {'en-CH':'testdesc2',
                'en-GB': 'testdescGB'},'type': 'type:course','interactionType': 'other', 'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2','ext:key3': 'value3'}}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)
        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-US')
        self.assertEqual(name_set.values()[0], 'testnameEN')
        self.assertEqual(name_set.keys()[1], 'en-FR')
        self.assertEqual(name_set.values()[1], 'testname2')

        self.assertEqual(desc_set.keys()[0], 'en-GB')
        self.assertEqual(desc_set.values()[0], 'testdescGB')
        self.assertEqual(desc_set.keys()[1], 'en-CH')
        self.assertEqual(desc_set.values()[1], 'testdesc2')

        self.do_activity_model(act.id,'act:food', 'Activity')        
        self.do_activity_definition_model(act, 'type:course', 'other')

        self.do_activity_definition_extensions_model(act, 'ext:key1', 'ext:key2', 'ext:key3',
            'value1', 'value2','value3')


    #Test activity with definition given wrong interactionType (won't create one)
    def test_activity_definition_wrong_interactionType(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 
                'id':'http://facebook.com','definition': {'name': {'en-US':'testname2'},
                'description': {'en-GB':'testdesc2'}, 'type': 'http://adlnet.gov/expapi/activities/cmi.interaction',
                'interactionType': 'intType2', 'correctResponsesPattern': 'response',
                'extensions': {'ext:key1': 'value1', 'ext:key2': 'value2','ext:key3': 'value3'}}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Activity definition interactionType intType2 is not valid')
     
    #Test activity with definition that is http://adlnet.gov/expapi/activities/cmi.interaction and true-false interactionType
    def test_activity_definition_cmiInteraction_true_false(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id':'act:fooe',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-US':'testdesc2'}, 
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'true-false',
                'correctResponsesPattern': ['true'] ,'extensions': {'ext:key1': 'value1', 'ext:key2': 'value2',
                'ext:key3': 'value3'}}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-FR')
        self.assertEqual(name_set.values()[0], 'testname2')

        self.assertEqual(desc_set.keys()[0], 'en-US')
        self.assertEqual(desc_set.values()[0], 'testdesc2')        

        self.do_activity_model(act.id,'act:fooe', 'Activity')                
        self.do_activity_definition_model(act, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'true-false')

        self.do_activity_definition_extensions_model(act, 'ext:key1', 'ext:key2', 'ext:key3',
            'value1','value2', 'value3')

        self.do_activity_definition_correctResponsePattern_model(act, ['true'])
    
    #Test activity with definition that is http://adlnet.gov/expapi/activities/cmi.interaction and multiple choice interactionType
    def test_activity_definition_cmiInteraction_multiple_choice(self):    
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id':'act:foof',
                'definition': {'name': {'en-US':'testname1'},'description': {'en-US':'testdesc1'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'choice',
                'correctResponsesPattern': ['golf', 'tetris'],'choices':[{'id': 'golf', 
                'description': {'en-US':'Golf Example', 'en-GB': 'GOLF'}},{'id': 'tetris',
                'description':{'en-US': 'Tetris Example', 'en-GB': 'TETRIS'}}, {'id':'facebook', 
                'description':{'en-US':'Facebook App', 'en-GB': 'FACEBOOK'}},{'id':'scrabble', 
                'description': {'en-US': 'Scrabble Example', 'en-GB': 'SCRABBLE'}}],'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2','ext:key3': 'value3'}}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-US')
        self.assertEqual(name_set.values()[0], 'testname1')

        self.assertEqual(desc_set.keys()[0], 'en-US')
        self.assertEqual(desc_set.values()[0], 'testdesc1')

        self.do_activity_model(act.id,'act:foof', 'Activity')
        self.do_activity_definition_model(act, 'http://adlnet.gov/expapi/activities/cmi.interaction', 'choice')

        self.do_activity_definition_extensions_model(act, 'ext:key1', 'ext:key2', 'ext:key3',
            'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_model(act, ['golf', 'tetris'])
        
        #Check model choice values
        clist = ['golf', 'tetris', 'facebook', 'scrabble']
        dlist = [{'en-GB': 'GOLF', 'en-US': 'Golf Example'}, {'en-GB': 'TETRIS', 'en-US': 'Tetris Example'},
        {'en-GB': 'FACEBOOK', 'en-US': 'Facebook App'}, {'en-GB': 'SCRABBLE', 'en-US': 'Scrabble Example'}]

        self.do_actvity_definition_choices_model(act, clist, dlist)        
        
    #Test activity with definition that is http://adlnet.gov/expapi/activities/cmi.interaction and multiple choice but missing choices (won't create it)
    def test_activity_definition_cmiInteraction_multiple_choice_no_choices(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 
                'id':'http://wikipedia.org','definition': {'name': {'en-US':'testname2'},
                'description': {'en-US':'testdesc2'},'type': 'http://adlnet.gov/expapi/activities/cmi.interaction',
                'interactionType': 'choice','correctResponsesPattern': ['golf', 'tetris'],
                'extensions': {'ext:key1': 'value1', 'ext:key2': 'value2','ext:key3': 'value3'}}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Activity definition is missing choices')

    #Test activity with definition that is http://adlnet.gov/expapi/activities/cmi.interaction and fill in interactionType
    def test_activity_definition_cmiInteraction_fill_in(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id':'act:foog',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'fill-in',
                'correctResponsesPattern': ['Fill in answer'],'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2', 'ext:key3': 'value3'}}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-FR')
        self.assertEqual(name_set.values()[0], 'testname2')

        self.assertEqual(desc_set.keys()[0], 'en-FR')
        self.assertEqual(desc_set.values()[0], 'testdesc2')

        self.do_activity_model(act.id,'act:foog', 'Activity')

        self.do_activity_definition_model(act, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'fill-in')

        self.do_activity_definition_extensions_model(act, 'ext:key1', 'ext:key2', 'ext:key3',
            'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_model(act, ['Fill in answer'])

    #Test activity with definition that is http://adlnet.gov/expapi/activities/cmi.interaction and long fill in interactionType
    def test_activity_definition_cmiInteraction_long_fill_in(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id':'act:fooh',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'fill-in',
                'correctResponsesPattern': ['Long fill in answer'],'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2','ext:key3': 'value3'}}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-FR')
        self.assertEqual(name_set.values()[0], 'testname2')

        self.assertEqual(desc_set.keys()[0], 'en-FR')
        self.assertEqual(desc_set.values()[0], 'testdesc2')

        self.do_activity_model(act.id, 'act:fooh', 'Activity')

        self.do_activity_definition_model(act, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'fill-in')

        self.do_activity_definition_extensions_model(act, 'ext:key1', 'ext:key2', 'ext:key3',
            'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_model(act, ['Long fill in answer'])

    #Test activity with definition that is http://adlnet.gov/expapi/activities/cmi.interaction and likert interactionType
    def test_activity_definition_cmiInteraction_likert(self):    
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id':'act:fooi',
                'definition': {'name': {'en-CH':'testname2'},'description': {'en-CH':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'likert',
                'correctResponsesPattern': ['likert_3'],'scale':[{'id': 'likert_0',
                'description': {'en-US':'Its OK', 'en-GB': 'Tis OK'}},{'id': 'likert_1',
                'description':{'en-US': 'Its Pretty Cool', 'en-GB':'Tis Pretty Cool'}}, {'id':'likert_2',
                'description':{'en-US':'Its Cool Cool', 'en-GB':'Tis Cool Cool'}},
                {'id':'likert_3', 'description': {'en-US': 'Its Gonna Change the World'}}]}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")

        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-CH')
        self.assertEqual(name_set.values()[0], 'testname2')

        self.assertEqual(desc_set.keys()[0], 'en-CH')
        self.assertEqual(desc_set.values()[0], 'testdesc2')

        self.do_activity_model(act.id, 'act:fooi', 'Activity')

        self.do_activity_definition_model(act, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'likert')

        self.do_activity_definition_correctResponsePattern_model(act, ['likert_3'])

        #Check model choice values
        clist = ['likert_0', 'likert_1', 'likert_2', 'likert_3']
        dlist = [{'en-GB': 'Tis OK', 'en-US': 'Its OK'},{'en-GB': 'Tis Pretty Cool', 'en-US': 'Its Pretty Cool'},
                 {'en-GB': 'Tis Cool Cool', 'en-US': 'Its Cool Cool'}, {'en-US': 'Its Gonna Change the World'}]
        
        self.do_actvity_definition_likert_model(act, clist, dlist)

    #Test activity with definition that is http://adlnet.gov/expapi/activities/cmi.interaction and matching interactionType
    def test_activity_definition_cmiInteraction_matching(self):    
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id':'act:fooj',
                'definition': {'name': {'en-CH':'testname2'},'description': {'en-CH':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'matching',
                'correctResponsesPattern': ['lou.3,tom.2,andy.1'],'source':[{'id': 'lou',
                'description': {'en-US':'Lou', 'it': 'Luigi'}},{'id': 'tom','description':{'en-US': 'Tom', 'it':'Tim'}},
                {'id':'andy', 'description':{'en-US':'Andy'}}],'target':[{'id':'1',
                'description':{'en-US': 'SCORM Engine'}},{'id':'2','description':{'en-US': 'Pure-sewage'}},
                {'id':'3', 'description':{'en-US': 'SCORM Cloud', 'en-CH': 'cloud'}}]}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")

        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-CH')
        self.assertEqual(name_set.values()[0], 'testname2')

        self.assertEqual(desc_set.keys()[0], 'en-CH')
        self.assertEqual(desc_set.values()[0], 'testdesc2')

        self.do_activity_model(act.id, 'act:fooj', 'Activity')

        self.do_activity_definition_model(act, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'matching')

        self.do_activity_definition_correctResponsePattern_model(act, ['lou.3,tom.2,andy.1'])

        #Check model choice values
        source_id_list = ['lou', 'tom', 'andy']
        source_desc_list = [{'en-US': 'Lou', 'it': 'Luigi'}, {'en-US': 'Tom', 'it': 'Tim'}, {'en-US': 'Andy'}]
        target_id_list = ['1','2','3']
        target_desc_list = [{"en-US": "SCORM Engine"},{"en-US": "Pure-sewage"},
                            {'en-US': 'SCORM Cloud', 'en-CH': 'cloud'}]

        self.do_actvity_definition_matching_model(act, source_id_list, source_desc_list,
                                                  target_id_list, target_desc_list)

    #Test activity with definition that is http://adlnet.gov/expapi/activities/cmi.interaction and performance interactionType
    def test_activity_definition_cmiInteraction_performance(self):    
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id':'act:fook',
                'definition': {'name': {'en-us':'testname2'},'description': {'en-us':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'performance',
                'correctResponsesPattern': ['pong.1,dg.10,lunch.4'],'steps':[{'id': 'pong',
                'description': {'en-US':'Net pong matches won', 'en-GB': 'won'}},{'id': 'dg',
                'description':{'en-US': 'Strokes over par in disc golf at Liberty'}},
                {'id':'lunch', 'description':{'en-US':'Lunch having been eaten'}}]}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description
        
        self.assertEqual(name_set.keys()[0], 'en-us')
        self.assertEqual(name_set.values()[0], 'testname2')

        self.assertEqual(desc_set.keys()[0], 'en-us')
        self.assertEqual(desc_set.values()[0], 'testdesc2')        

        self.do_activity_model(act.id, 'act:fook', 'Activity')

        self.do_activity_definition_model(act, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'performance')

        self.do_activity_definition_correctResponsePattern_model(act, ['pong.1,dg.10,lunch.4'])

        #Check model choice values
        slist = ['pong', 'dg', 'lunch']
        dlist = [{'en-GB': 'won', 'en-US': 'Net pong matches won'}, {'en-US': 'Strokes over par in disc golf at Liberty'},
                    {'en-US': 'Lunch having been eaten'}]
        
        self.do_actvity_definition_performance_model(act, slist, dlist)

    # Test activity with definition that is http://adlnet.gov/expapi/activities/cmi.interaction and sequencing interactionType
    def test_activity_definition_cmiInteraction_sequencing(self):    
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id':'act:fool',
                'definition': {'name': {'en-GB':'testname2'},'description': {'en-GB':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'sequencing',
                'correctResponsesPattern': ['lou,tom,andy,aaron'],'choices':[{'id': 'lou',
                'description': {'en-US':'Lou'}},{'id': 'tom','description':{'en-US': 'Tom'}},
                {'id':'andy', 'description':{'en-US':'Andy'}},{'id':'aaron',
                'description':{'en-US':'Aaron', 'en-GB': 'Erin'}}]}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-GB')
        self.assertEqual(name_set.values()[0], 'testname2')

        self.assertEqual(desc_set.keys()[0], 'en-GB')
        self.assertEqual(desc_set.values()[0], 'testdesc2')

        self.do_activity_model(act.id, 'act:fool', 'Activity')

        self.do_activity_definition_model(act, 'http://adlnet.gov/expapi/activities/cmi.interaction', 'sequencing')

        self.do_activity_definition_correctResponsePattern_model(act, ['lou,tom,andy,aaron'])
        #Check model choice values
        clist = ['lou', 'tom', 'andy', 'aaron']
        dlist = [{"en-US": "Lou"},{"en-US": "Tom"},{"en-US": "Andy"}, {'en-GB': 'Erin', 'en-US': 'Aaron'}]
        self.do_actvity_definition_choices_model(act, clist, dlist)

    #Test activity with definition that is http://adlnet.gov/expapi/activities/cmi.interaction and numeric interactionType
    def test_activity_definition_cmiInteraction_numeric(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id':'act:foom',
                'definition': {'name': {'en-CH':'testname2'},'description': {'en-CH':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'numeric','correctResponsesPattern': ['4'],
                'extensions': {'ext:key1': 'value1', 'ext:key2': 'value2','ext:key3': 'value3'}}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-CH')
        self.assertEqual(name_set.values()[0], 'testname2')

        self.assertEqual(desc_set.keys()[0], 'en-CH')
        self.assertEqual(desc_set.values()[0], 'testdesc2')

        self.do_activity_model(act.id, 'act:foom', 'Activity')

        self.do_activity_definition_model(act, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'numeric')

        self.do_activity_definition_extensions_model(act, 'ext:key1', 'ext:key2', 'ext:key3',
            'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_model(act, ['4'])

    #Test activity with definition that is http://adlnet.gov/expapi/activities/cmi.interaction and other interactionType
    def test_activity_definition_cmiInteraction_other(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id': 'act:foon',
                'definition': {'name': {'en-FR':'testname2'},'description': {'en-FR':'testdesc2'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other',
                'correctResponsesPattern': ['(35.937432,-86.868896)'],'extensions': {'ext:key1': 'value1',
                'ext:key2': 'value2','ext:key3': 'value3'}}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-FR')
        self.assertEqual(name_set.values()[0], 'testname2')

        self.assertEqual(desc_set.keys()[0], 'en-FR')
        self.assertEqual(desc_set.values()[0], 'testdesc2')

        self.do_activity_model(act.id, 'act:foon', 'Activity')

        self.do_activity_definition_model(act, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'other')

        self.do_activity_definition_extensions_model(act, 'ext:key1', 'ext:key2', 'ext:key3',
            'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_model(act, ['(35.937432,-86.868896)'])

    # Should be the same, no auth required
    def test_multiple_activities(self):
        stmt_list = []
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob'}})

        stmt2 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob'}})

        stmt3 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob'}})

        stmt4 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foon'}})
        stmt_list.append(stmt1)
        stmt_list.append(stmt2)
        stmt_list.append(stmt3)
        stmt_list.append(stmt4)

        response = self.client.post(reverse(views.statements), stmt_list, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_ids = json.loads(response.content)
        st1 = models.Statement.objects.get(statement_id=st_ids[0])
        st2 = models.Statement.objects.get(statement_id=st_ids[1])
        st3 = models.Statement.objects.get(statement_id=st_ids[2])
        st4 = models.Statement.objects.get(statement_id=st_ids[3])
        act1 = models.Activity.objects.get(id=st1.object_activity.id)
        act2 = models.Activity.objects.get(id=st2.object_activity.id)
        act3 = models.Activity.objects.get(id=st3.object_activity.id)
        act4 = models.Activity.objects.get(id=st4.object_activity.id)

        self.assertEqual(act1.id, act2.id)
        self.assertEqual(act1.id, act3.id)
        self.assertEqual(act2.id, act3.id)
        self.assertNotEqual(act1.id, act4.id)

    def test_language_map_description_name(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType': 'Activity', 'id': 'act:foz',
                'definition': {'name': {'en-US':'actname'},'description': {'en-us':'actdesc'},
                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other',
                    'correctResponsesPattern': ['(35,-86)']}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        name_set = act.activity_definition_name
        desc_set = act.activity_definition_description

        self.assertEqual(name_set.keys()[0], 'en-US')
        self.assertEqual(name_set.values()[0], 'actname')

        self.assertEqual(desc_set.keys()[0], 'en-us')
        self.assertEqual(desc_set.values()[0], 'actdesc')
        self.do_activity_model(act.id, 'act:foz', 'Activity')

        self.do_activity_definition_model(act, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'other')

    def test_multiple_activities_update_name(self):
        stmt_list = []
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-US':'actname'},'description': {'en-us':'actdesc'}, 
            'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}})

        stmt2 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-US':'actname2'},'description': {'en-us':'actdesc'}, 
            'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}})

        stmt_list.append(stmt1)
        stmt_list.append(stmt2)

        response = self.client.post(reverse(views.statements), stmt_list, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_ids = json.loads(response.content)
        st1 = models.Statement.objects.get(statement_id=st_ids[0])
        st2 = models.Statement.objects.get(statement_id=st_ids[1])        
        act1 = models.Activity.objects.get(id=st1.object_activity.id)
        act2 = models.Activity.objects.get(id=st2.object_activity.id)

        self.do_activity_model(act1.id, 'act:foob', 'Activity')

        name_set1 = act1.activity_definition_name
        desc_set1 = act1.activity_definition_description
        
        self.assertEqual(name_set1.keys()[0], 'en-US')
        self.assertEqual(name_set1.values()[0], 'actname2')

        self.assertEqual(desc_set1.keys()[0], 'en-us')
        self.assertEqual(desc_set1.values()[0], 'actdesc')        


        self.do_activity_definition_model(act1, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'other')

        self.do_activity_model(act2.id, 'act:foob', 'Activity')

        name_set2 = act2.activity_definition_name
        desc_set2 = act2.activity_definition_description
        
        self.assertEqual(name_set2.keys()[0], 'en-US')
        self.assertEqual(name_set2.values()[0], 'actname2')

        self.assertEqual(desc_set2.keys()[0], 'en-us')
        self.assertEqual(desc_set2.values()[0], 'actdesc')        

        self.do_activity_definition_model(act2, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'other')

        self.assertEqual(act1, act2)
        
    def test_multiple_activities_update_desc(self):
        stmt_list = []
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foobe',
            'definition':{'name': {'en-US':'actname'},'description': {'en-us':'actdesc'}, 
            'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}})

        stmt2 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foobe',
            'definition':{'name': {'en-US':'actname'},'description': {'en-us':'actdesc2'}, 
            'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}})

        stmt_list.append(stmt1)
        stmt_list.append(stmt2)

        response = self.client.post(reverse(views.statements), stmt_list, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_ids = json.loads(response.content)
        st1 = models.Statement.objects.get(statement_id=st_ids[0])
        st2 = models.Statement.objects.get(statement_id=st_ids[1])        
        act1 = models.Activity.objects.get(id=st1.object_activity.id)
        act2 = models.Activity.objects.get(id=st2.object_activity.id)

        self.do_activity_model(act1.id, 'act:foobe', 'Activity')

        name_set1 = act1.activity_definition_name
        desc_set1 = act1.activity_definition_description
        
        self.assertEqual(name_set1.keys()[0], 'en-US')
        self.assertEqual(name_set1.values()[0], 'actname')

        self.assertEqual(desc_set1.keys()[0], 'en-us')
        self.assertEqual(desc_set1.values()[0], 'actdesc2')
        self.do_activity_definition_model(act1, 'http://adlnet.gov/expapi/activities/cmi.interaction', 'other')

        self.do_activity_model(act2.id, 'act:foobe', 'Activity')

        name_set2 = act2.activity_definition_name
        desc_set2 = act2.activity_definition_description

        self.assertEqual(name_set2.keys()[0], 'en-US')
        self.assertEqual(name_set2.values()[0], 'actname')

        self.assertEqual(desc_set2.keys()[0], 'en-us')
        self.assertEqual(desc_set2.values()[0], 'actdesc2')        
        self.do_activity_definition_model(act2, 'http://adlnet.gov/expapi/activities/cmi.interaction', 'other')

        self.assertEqual(act1, act2)

    def test_multiple_activities_update_both(self):
        stmt_list = []
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname'},'description': {'en-FR':'actdesc'}, 
            'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}})

        stmt2 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname2'},'description': {'en-FR':'actdesc2'}, 
            'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}})

        stmt_list.append(stmt1)
        stmt_list.append(stmt2)

        response = self.client.post(reverse(views.statements), stmt_list, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_ids = json.loads(response.content)
        st1 = models.Statement.objects.get(statement_id=st_ids[0])
        st2 = models.Statement.objects.get(statement_id=st_ids[1])        
        act1 = models.Activity.objects.get(id=st1.object_activity.id)
        act2 = models.Activity.objects.get(id=st2.object_activity.id)

        self.do_activity_model(act1.id, 'act:foob', 'Activity')

        name_set1 = act1.activity_definition_name
        desc_set1 = act1.activity_definition_description
        
        self.assertEqual(name_set1.keys()[0], 'en-CH')
        self.assertEqual(name_set1.values()[0], 'actname2')

        self.assertEqual(desc_set1.keys()[0], 'en-FR')
        self.assertEqual(desc_set1.values()[0], 'actdesc2')

        self.do_activity_definition_model(act1, 'http://adlnet.gov/expapi/activities/cmi.interaction', 'other')

        self.do_activity_model(act2.id, 'act:foob', 'Activity')

        name_set2 = act2.activity_definition_name
        desc_set2 = act2.activity_definition_description
        
        self.assertEqual(name_set2.keys()[0], 'en-CH')
        self.assertEqual(name_set2.values()[0], 'actname2')

        self.assertEqual(desc_set2.keys()[0], 'en-FR')
        self.assertEqual(desc_set2.values()[0], 'actdesc2')         
        self.do_activity_definition_model(act2,'http://adlnet.gov/expapi/activities/cmi.interaction',
            'other')

        self.assertEqual(act1, act2)

    def test_multiple_activities_update_both_and_add(self):
        stmt_list = []
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname'},'description': {'en-FR':'actdesc'}, 
            'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}})

        stmt2 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname2', 'en-US': 'altname'},'description': {'en-FR':'actdesc2', 'en-GB': 'altdesc'}, 
            'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other','correctResponsesPattern': ['(35,-86)']}}})

        stmt_list.append(stmt1)
        stmt_list.append(stmt2)

        response = self.client.post(reverse(views.statements), stmt_list, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_ids = json.loads(response.content)
        st1 = models.Statement.objects.get(statement_id=st_ids[0])
        st2 = models.Statement.objects.get(statement_id=st_ids[1])        
        act1 = models.Activity.objects.get(id=st1.object_activity.id)
        act2 = models.Activity.objects.get(id=st2.object_activity.id)

        self.do_activity_model(act1.id, 'act:foob', 'Activity')

        name_set1 = act1.activity_definition_name
        desc_set1 = act1.activity_definition_description
        
        self.assertEqual(name_set1.keys()[1], 'en-CH')
        self.assertEqual(name_set1.values()[1], 'actname2')
        self.assertEqual(name_set1.keys()[0], 'en-US')
        self.assertEqual(name_set1.values()[0], 'altname')

        self.assertEqual(desc_set1.keys()[1], 'en-FR')
        self.assertEqual(desc_set1.values()[1], 'actdesc2')
        self.assertEqual(desc_set1.keys()[0], 'en-GB')
        self.assertEqual(desc_set1.values()[0], 'altdesc')

        self.do_activity_definition_model(act1, 'http://adlnet.gov/expapi/activities/cmi.interaction',
            'other')

        self.do_activity_model(act2.id, 'act:foob', 'Activity')

        name_set2 = act2.activity_definition_name
        desc_set2 = act2.activity_definition_description

        self.assertEqual(name_set2.keys()[1], 'en-CH')
        self.assertEqual(name_set2.values()[1], 'actname2')
        self.assertEqual(name_set2.keys()[0], 'en-US')
        self.assertEqual(name_set2.values()[0], 'altname')

        self.assertEqual(desc_set2.keys()[1], 'en-FR')
        self.assertEqual(desc_set2.values()[1], 'actdesc2')
        self.assertEqual(desc_set2.keys()[0], 'en-GB')
        self.assertEqual(desc_set2.values()[0], 'altdesc')

        self.do_activity_definition_model(act2,'http://adlnet.gov/expapi/activities/cmi.interaction',
            'other')

        self.assertEqual(act1, act2)
        
    def test_del_act(self):
        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname'},'description': {'en-FR':'actdesc'}, 
            'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other',
            'correctResponsesPattern': ['(35,-86)']}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = models.Statement.objects.get(statement_id=st_id[0])
        act = models.Activity.objects.get(id=st.object_activity.id)

        self.assertEqual(1, len(models.Activity.objects.all()))
        act.delete()
        self.assertEqual(0, len(models.Activity.objects.all()))

    def test_same_act_def_different_auth(self):
        username = "otheruser"
        email = "other@tester.com"
        password = "test"
        auth_new = "Basic %s" % base64.b64encode("%s:%s" % (username, password))
        form = {"username":username, "email":email,"password":password,"password2":password}
        response = self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0.0")

        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:t@t.com", "name":"bob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname'},'description': {'en-FR':'actdesc'}, 
            'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other',
            'correctResponsesPattern': ['(35,-86)']}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)

        stmt1 = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:l@l.com", "name":"lob"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed","display": {"en-US":"passed"}},
            "object": {'objectType':'Activity', 'id': 'act:foob',
            'definition':{'name': {'en-CH':'actname'},'description': {'en-FR':'actdesc'}, 
            'type': 'http://adlnet.gov/expapi/activities/cmi.interaction','interactionType': 'other',
            'correctResponsesPattern': ['(35,-86)']}}})

        response = self.client.post(reverse(views.statements), stmt1, content_type="application/json",
            Authorization=auth_new, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
