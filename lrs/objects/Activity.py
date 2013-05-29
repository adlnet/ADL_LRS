import json
import urllib2
from StringIO import StringIO
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from lrs import models, exceptions
from lrs.util import uri
import pdb
import pprint

class Activity():
    # Activity definition required fields - all optional now
    # ADRFs = ['name', 'description', 'type']

    # Use single transaction for all the work done in function
    @transaction.commit_on_success
    def __init__(self, data, auth=None, define=True):
        if auth:
            if auth.__class__.__name__ == 'agent':
                self.auth = auth.name
            else:
                self.auth = auth.username
        else:
            self.auth = None
        self.params = data
        self.define = define
        if not isinstance(data, dict):
            self.params = self.parse(data)
        self.populate(self.params)

    # Make sure initial data being received is can be transformed into a dict-should ALWAYS be
    # incoming JSON because class is only called from Statement class
    def parse(self,data):        
        try:
            params = json.loads(data)
        except Exception, e:
            err_msg = "Error parsing the Activity object. Expecting json. Received: %s which is %s" % (data, type(data))
            raise exceptions.ParamError(err_msg)
        return params

    # Retrieve JSON data from ID
    def get_data_from_act_id(self,act_id):
        resolves = True
        act_json = {}

        # See if id resolves
        try:
            req = urllib2.Request(act_id)
            req.add_header('Accept', 'application/json, */*')
            act_resp = urllib2.urlopen(req, timeout=10)
        except Exception, e:
            # Doesn't resolve-hopefully data is in payload
            resolves = False
        else:
            # If it resolves then try parsing JSON from it
            try:
                act_json = json.loads(act_resp.read())
            except Exception, e:
                # Resolves but no data to retrieve - this is OK
                pass
        return act_json

    #Save activity definition to DB
    def save_activity_definition_to_db(self,act_def_type, intType, moreInfo):
        created = True
        try:
            self.activity.activity_definition
            created = False
        except:
            actdef = models.activity_definition(activity_definition_type=act_def_type,
                  interactionType=intType, activity=self.activity, moreInfo=moreInfo)
            actdef.save()

        return created

    def check_activity_definition_value(self, new_name_value, existing_name_value):
        return new_name_value == existing_name_value

    def update_activity_name_and_description(self, new_activity, existing_activity):
        # Try grabbing the activity definition (these aren't required)
        existing_act_def = None        
        try:
            existing_act_def = models.activity_definition.objects.get(activity=existing_activity)
        except models.activity_definition.DoesNotExist:
            pass

        # If there is an existing activity definition and the names or descriptions are different,
        # update it with new name and/or description info
        if existing_act_def:
            # Get list of existing name lang maps
            existing_name_lang_map_set = existing_act_def.name.all()

            # Make lists of keys and values from existing name lang maps
            existing_name_key_set = existing_name_lang_map_set.values_list('key', flat=True)

            # Get list of existing desc lang maps
            existing_desc_lang_map_set = existing_act_def.description.all()

            # Make lists of keys and values from existing desc lang maps
            existing_desc_key_set = existing_desc_lang_map_set.values_list('key', flat=True)

            # Loop through all language maps in name
            the_definition = new_activity
            
            try:
                the_names = the_definition['name']
            except KeyError:
                err_msg = "Activity definition has no name attribute"
                raise exceptions.ParamError(err_msg)
            for new_name_lang_map in the_names.items():
                # If there is already an entry in the same language
                if new_name_lang_map[0] in existing_name_key_set:
                    name_same = True                    
                    # Retrieve existing language map with same key (all in the existing act_def)
                    existing_lang_map = existing_act_def.name.get(key=new_name_lang_map[0])
                    name_same = self.check_activity_definition_value(new_name_lang_map[1], existing_lang_map.value)
                    # If names are different, update the language map with the new name
                    if not name_same:
                        existing_act_def.name.filter(id=existing_lang_map.id).update(value=new_name_lang_map[1])
                # Else it's a new lang map and needs added
                else:
                    existing_act_def.name.create(key=new_name_lang_map[0], value=new_name_lang_map[1])
                    existing_act_def.save()                    

            # Loop through all language maps in description
            try:
                the_descriptions = the_definition['description']
            except KeyError:
                err_msg = "Activity definition has no description attribute"
                raise exceptions.ParamError()
            for new_desc_lang_map in the_descriptions.items():
                # If there is already an entry in the same language
                if new_desc_lang_map[0] in existing_desc_key_set:
                    desc_same = False
                    # Retrieve existing language map with same key (all in the existing act_def)
                    existing_lang_map = existing_act_def.description.get(key=new_desc_lang_map[0])
                    desc_same = self.check_activity_definition_value(new_desc_lang_map[1], existing_lang_map.value)
                    # If desc are different, update the langage map with the new desc
                    if not desc_same:
                        existing_act_def.description.filter(id=existing_lang_map.id).update(value=new_desc_lang_map[1])
                else:
                    existing_act_def.description.create(key=new_desc_lang_map[0], value=new_desc_lang_map[1])
                    existing_act_def.save()                    

    #Once JSON is verified, populate the activity objects
    def populate(self, the_object):        
        # Must include activity_id - set object's activity_id
        # Make sure it's a URI
        try:
            activity_id = the_object['id']
            if not uri.validate_uri(activity_id):
                raise exceptions.ParamError('Activity ID %s is not a valid URI' % activity_id)
        except KeyError:
            err_msg = "No id provided, must provide 'id' field"
            raise exceptions.ParamError(err_msg)

        # If allowed to define activities-create or get the global version
        if self.define:
            self.activity, act_created = models.activity.objects.get_or_create(activity_id=activity_id,
                global_representation=True)
        else:
            # Not allowed to create global version b/c don't have define permissions
            self.activity = models.activity(activity_id=activity_id, global_representation=False)
            self.activity.save()
            act_created = False

        if act_created:
            if self.auth:
                self.activity.authoritative = self.auth
                self.activity.save()

        # Try grabbing any activity data from the activity ID
        activity_definition = self.get_data_from_act_id(activity_id)

        # If there is a definition in the payload, grab it and merge with any data from activity ID
        # (payload data overrides ID data)
        if 'definition' in the_object:
            data_from_payload = the_object['definition']
            activity_definition = dict(activity_definition.items() + data_from_payload.items())

        # If there is a definition-populate the definition
        if activity_definition:
            self.populate_definition(activity_definition, act_created)
        
    # Save language map object for activity definition name or description
    def save_lang_map(self, lang_map, parent, lang_map_type):
        if lang_map_type == 'choice':
            language_map = models.ActivityDefinitionChoiceDesc.objects.create(key = lang_map[0],
                value = lang_map[1], content_object=parent)
        elif lang_map_type == 'scale':
            language_map = models.ActivityDefinitionScaleDesc.objects.create(key = lang_map[0],
                value = lang_map[1],content_object=parent)        
        elif lang_map_type == 'step':
            language_map = models.ActivityDefinitionStepDesc.objects.create(key = lang_map[0],
                value = lang_map[1],content_object=parent)
        elif lang_map_type == 'source':
            language_map = models.ActivityDefinitionSourceDesc.objects.create(key = lang_map[0],
                value = lang_map[1],content_object=parent)
        elif lang_map_type == 'target':            
            language_map = models.ActivityDefinitionTargetDesc.objects.create(key = lang_map[0],
                value = lang_map[1],content_object=parent)
        return language_map

    def validate_cmi_interaction(self, act_def, act_created):
        interaction_flag = None
        scormInteractionTypes = ['true-false', 'choice', 'fill-in', 'long-fill-in',
                                 'matching', 'performance', 'sequencing', 'likert', 'numeric',
                                 'other']
    
        #Check if valid SCORM interactionType
        if act_def['interactionType'] not in scormInteractionTypes:
            if act_created:
                self.activity.delete()
                self.activity = None
            err_msg = "Activity definition interactionType not valid"
            raise exceptions.ParamError(err_msg)

        #Must have correctResponsesPattern if they have a valid interactionType
        try:
            act_def['correctResponsesPattern']  
        except KeyError: 
            if act_created:
                self.activity.delete()
                self.activity = None   
            err_msg = "Activity definition missing correctResponsesPattern"
            raise exceptions.ParamError(err_msg)    

        #Multiple choice and sequencing must have choices
        if act_def['interactionType'] == 'choice' or \
            act_def['interactionType'] == 'sequencing':
                try:
                    act_def['choices']
                except KeyError:
                    if act_created:
                        self.activity.delete()
                        self.activity = None
                    err_msg = "Activity definition missing choices"
                    raise exceptions.ParamError(err_msg)
                interaction_flag = 'choices' 

        #Matching must have both source and target
        elif act_def['interactionType'] == 'matching':
            try:
                act_def['source']
                act_def['target']
            except KeyError:
                if act_created:
                    self.activity.delete()
                    self.activity = None
                err_msg = "Activity definition missing source/target for matching"
                raise exceptions.ParamError(err_msg)
            interaction_flag = 'source'

        #Performance must have steps
        elif act_def['interactionType'] == 'performance':
            try:
                act_def['steps']
            except KeyError:
                if act_created:
                    self.activity.delete()
                    self.activity = None
                err_msg = "Activity definition missing steps for performance"
                raise exceptions.ParamError(err_msg)    
            interaction_flag = 'steps'

        #Likert must have scale
        elif act_def['interactionType'] == 'likert':
            try:
                act_def['scale']
            except KeyError:
                if act_created:
                    self.activity.delete()
                    self.activity = None
                err_msg = "Activity definition missing scale for likert"
                raise exceptions.ParamError(err_msg)
            interaction_flag = 'scale'
        return interaction_flag

    #Populate definition either from JSON or validated XML
    def populate_definition(self, act_def, act_created):
        # only update existing def stuff if request has authority to do so
        if not act_created and (self.activity.authoritative != '' and self.activity.authoritative != self.auth):
            err_msg = "This ActivityID already exists, and you do not have the correct authority to create or update it."
            raise exceptions.Forbidden(err_msg)

        act_def_type = ''
        if 'type' in act_def:
            act_def_type = act_def['type']
            if not uri.validate_uri(act_def_type):
                raise exceptions.ParamError('Activity definition type %s is not a valid URI' % act_def_type)
        
            #If the type is cmi.interaction, have to check interactionType
            interaction_flag = None
            if act_def_type == 'http://adlnet.gov/expapi/activities/cmi.interaction':
                interaction_flag = self.validate_cmi_interaction(act_def, act_created)

        if 'moreInfo' in act_def:
            moreInfo = act_def['moreInfo']
            if not uri.validate_uri(moreInfo):
                raise exceptions.ParamError('moreInfo %s is not a valid URI' % moreInfo)
        else:
            moreInfo = ''

        act_def_created = self.save_activity_definition_to_db(act_def_type, act_def.get('interactionType', ''),
            moreInfo)

        if not act_created: 
            if self.activity.authoritative == '' or self.activity.authoritative == self.auth:
                # Update name and desc if needed
                self.update_activity_name_and_description(act_def, self.activity)
            else:
                err_msg = "This ActivityID already exists, and you do not have the correct authority to create or update it."
                raise exceptions.Forbidden(err_msg)
        else:
            # If created and have permisson to (re)define activities
            if self.define:
                # Save activity definition name and description
                if 'name' in act_def:
                    for name_lang_map in act_def['name'].items():
                        if isinstance(name_lang_map, tuple):
                            n = models.name_lang(key=name_lang_map[0],
                                          value=name_lang_map[1],
                                          content_object=self.activity.activity_definition)
                            n.save()
                        else:
                            err_msg = "Activity with id %s has a name that is not a language map" % self.activity.activity_id
                            raise exceptions.ParamError(err_msg)

                if 'description' in act_def:
                    for desc_lang_map in act_def['description'].items():
                        if isinstance(desc_lang_map, tuple):
                            d = models.desc_lang(key=desc_lang_map[0],
                                          value=desc_lang_map[1],
                                          content_object=self.activity.activity_definition)
                            d.save()
                        else:
                            err_msg = "Activity with id %s has a description that is not a language map" % self.activity.activity_id
                            raise exceptions.ParamError(err_msg)
        
        #If there is a correctResponsesPattern then save the pattern
        if act_def_created and 'correctResponsesPattern' in act_def.keys():
            self.populate_correctResponsesPattern(act_def, interaction_flag)
        #See if activity definition has extensions
        if act_def_created and 'extensions' in act_def.keys():
            self.populate_extensions(act_def) 

    def populate_correctResponsesPattern(self, act_def, interactionFlag):
        crp = models.activity_def_correctresponsespattern(activity_definition=self.activity.activity_definition)
        crp.save()

        #For each answer in the pattern save it
        for i in act_def['correctResponsesPattern']:
            answer = models.correctresponsespattern_answer(answer=i, correctresponsespattern=crp)
            answer.save()

        #Depending on which type of interaction, save the unique fields accordingly
        if interactionFlag == 'choices' or interactionFlag == 'sequencing':
            for c in act_def['choices']:
                choice = models.activity_definition_choice(choice_id=c['id'], activity_definition=self.activity.activity_definition)
                choice.save()
                #Save description as string, not a dictionary
                for desc_lang_map in c['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self.save_lang_map(desc_lang_map, choice, "choice")
                        choice.save()
                    else:
                        choice.delete()
                        err_msg = "Choice description must be a language map"
                        raise exceptions.ParamError(err_msg)

        elif interactionFlag == 'scale':
            for s in act_def['scale']:
                scale = models.activity_definition_scale(scale_id=s['id'], activity_definition=self.activity.activity_definition)        
                scale.save()
                # Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self.save_lang_map(desc_lang_map, scale, "scale")
                        scale.save()
                    else:
                        scale.delete()
                        err_msg = "Scale description must be a language map"
                        raise exceptions.ParamError(err_msg)

        elif interactionFlag == 'steps':
            for s in act_def['steps']:
                step = models.activity_definition_step(step_id=s['id'], activity_definition=self.activity.activity_definition)
                step.save()
                #Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self.save_lang_map(desc_lang_map, step, "step")
                        step.save()
                    else:
                        step.delete()
                        err_msg = "Step description must be a language map"
                        raise exceptions.ParamError(err_msg)  

        elif interactionFlag == 'source':
            for s in act_def['source']:
                source = models.activity_definition_source(source_id=s['id'], activity_definition=self.activity.activity_definition)
                source.save()                        
                #Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self.save_lang_map(desc_lang_map, source, "source")
                        source.save()
                    else:
                        source.delete()
                        err_msg = "Source description must be a language map"
                        raise exceptions.ParamError(err_msg)

            for t in act_def['target']:
                target = models.activity_definition_target(target_id=t['id'], activity_definition=self.activity.activity_definition)
                target.save()
                #Save description as string, not a dictionary
                for desc_lang_map in t['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self.save_lang_map(desc_lang_map, target, "target")
                        target.save()
                    else:
                        target.delete()
                        err_msg = "Target description must be a language map"
                        raise exceptions.ParamError(err_msg)

    def populate_extensions(self, act_def):
        for k, v in act_def['extensions'].items():
            if not uri.validate_uri(k):
                err_msg = "Extension ID %s is not a valid URI" % k
                raise exceptions.ParamError(err_msg)

            act_def_ext = models.ActivityDefinitionExtensions.objects.create(key=k, value=v,
                content_object=self.activity.activity_definition)