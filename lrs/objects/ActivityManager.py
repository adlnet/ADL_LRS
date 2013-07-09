import json
import urllib2
from StringIO import StringIO
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from lrs import models, exceptions
from lrs.util import uri

class ActivityManager():
    # Use single transaction for all the work done in function
    @transaction.commit_on_success
    def __init__(self, data, auth=None, define=True):
        if auth:
            if auth.__class__.__name__ == 'Agent':
                self.auth = auth.name
            else:
                self.auth = auth.username
        else:
            self.auth = None
        self.define = define
        if not isinstance(data, dict):
            data = self.parse(data)
        self.populate(data)

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
    def save_activity_definition_to_db(self,act_def_type, int_type, more_info):
        created = True        
        # Have to check if the activity already has an activity definition. Can only update name and
        # description in definition, so no matter what the user's scope is, if the activity def already
        # exists you can't create another one
        if (self.Activity.activity_definition_type or self.Activity.activity_definition_moreInfo or
                self.Activity.activity_definition_interactionType):
            created = False
        else:
            self.Activity.activity_definition_type = act_def_type
            self.Activity.activity_definition_moreInfo = more_info
            self.Activity.activity_definition_interactionType = int_type
            self.Activity.save()
        return created

    def check_activity_definition_value(self, new_name_value, existing_name_value):
        return new_name_value == existing_name_value

    def update_activity_name_and_description(self, incoming_definition):
        # If there is an existing activity definition and the names or descriptions are different,
        # update it with new name and/or description info
        # Get list of existing name lang maps
        existing_name_lang_set = self.Activity.activitydefinitionnamelangmap_set.all()

        # Make lists of keys and values from existing name lang maps
        existing_name_key_set = existing_name_lang_set.values_list('key', flat=True)

        # Get list of existing desc lang maps
        existing_desc_lang_set = self.Activity.activitydefinitiondesclangmap_set.all()

        # Make lists of keys and values from existing desc lang maps
        existing_desc_key_set = existing_desc_lang_set.values_list('key', flat=True)

        the_names = incoming_definition['name']
        
        for new_name_lang_map in the_names.items():
            # If there is already an entry in the same language
            if new_name_lang_map[0] in existing_name_key_set:
                name_same = True
                # Retrieve existing language map with same key (all in the existing act_def)
                existing_lang_map = models.ActivityDefinitionNameLangMap.objects.get(key=new_name_lang_map[0],
                    activity=self.Activity)
                # Once you retrieve the existing name_map via the key, check if the value is the same
                name_same = self.check_activity_definition_value(new_name_lang_map[1], existing_lang_map.value)
                # If names are different, update the language map with the new name
                if not name_same:
                    existing_lang_map.value = new_name_lang_map[1]
                    existing_lang_map.save()
            # Else it's a new lang map and needs added
            else:
                models.ActivityDefinitionNameLangMap.objects.create(key=new_name_lang_map[0],
                    value=new_name_lang_map[1],activity=self.Activity)

        the_descriptions = incoming_definition['description']
        for new_desc_lang_map in the_descriptions.items():
            # If there is already an entry in the same language
            if new_desc_lang_map[0] in existing_desc_key_set:
                desc_same = True
                # Retrieve existing language map with same key (all in the existing act_def)
                existing_lang_map = models.ActivityDefinitionDescLangMap.objects.get(key=new_desc_lang_map[0],
                    activity=self.Activity)
                desc_same = self.check_activity_definition_value(new_desc_lang_map[1], existing_lang_map.value)
                # If desc are different, update the langage map with the new desc
                if not desc_same:
                    existing_lang_map.value = new_desc_lang_map[1]
                    existing_lang_map.save()
            # Else it's a new lang map and needs added
            else:
                models.ActivityDefinitionDescLangMap.objects.create(key=new_desc_lang_map[0],
                    value=new_desc_lang_map[1], activity=self.Activity)

    #Once JSON is verified, populate the activity objects
    def populate(self, the_object):        
        activity_id = the_object['id']

        # If allowed to define activities-create or get the global version
        if self.define:
            self.Activity, act_created = models.Activity.objects.get_or_create(activity_id=activity_id,
                global_representation=True)
        else:
            # Not allowed to create global version b/c don't have define permissions
            self.Activity = models.Activity.objects.create(activity_id=activity_id, global_representation=False)
            act_created = False

        if act_created:
            if self.auth:
                self.Activity.authoritative = self.auth
                self.Activity.save()

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
            language_map = models.ActivityDefinitionChoiceDesc.objects.create(key=lang_map[0],
                value = lang_map[1],act_def_choice=parent)
        elif lang_map_type == 'scale':
            language_map = models.ActivityDefinitionScaleDesc.objects.create(key=lang_map[0],
                value = lang_map[1],act_def_scale=parent)        
        elif lang_map_type == 'step':
            language_map = models.ActivityDefinitionStepDesc.objects.create(key=lang_map[0],
                value = lang_map[1],act_def_step=parent)
        elif lang_map_type == 'source':
            language_map = models.ActivityDefinitionSourceDesc.objects.create(key=lang_map[0],
                value = lang_map[1],act_def_source=parent)
        elif lang_map_type == 'target':            
            language_map = models.ActivityDefinitionTargetDesc.objects.create(key=lang_map[0],
                value = lang_map[1],act_def_target=parent)
        return language_map

    def validate_cmi_interaction(self, act_def, act_created):
        interaction_flag = None

        #Multiple choice and sequencing must have choices
        if act_def['interactionType'] == 'choice' or \
            act_def['interactionType'] == 'sequencing':
                interaction_flag = 'choices' 
        #Matching must have both source and target
        elif act_def['interactionType'] == 'matching':
            interaction_flag = 'source'
        #Performance must have steps
        elif act_def['interactionType'] == 'performance':
            interaction_flag = 'steps'
        #Likert must have scale
        elif act_def['interactionType'] == 'likert':
            interaction_flag = 'scale'
        return interaction_flag

    #Populate definition either from JSON or validated XML
    def populate_definition(self, act_def, act_created):
        # only update existing def stuff if request has authority to do so
        if not act_created and (self.Activity.authoritative != '' and self.Activity.authoritative != self.auth):
            err_msg = "This ActivityID already exists, and you do not have the correct authority to create or update it."
            raise exceptions.Forbidden(err_msg)

        # validate type if it exists
        act_def_type = ''
        if 'type' in act_def:
            act_def_type = act_def['type']

            #If the type is cmi.interaction, have to check interactionType
            interaction_flag = None
            if act_def_type == 'http://adlnet.gov/expapi/activities/cmi.interaction':
                interaction_flag = self.validate_cmi_interaction(act_def, act_created)

        # validate moreInfo if it exists
        if 'moreInfo' in act_def:
            more_info = act_def['moreInfo']
        else:
            more_info = ''

        # return t/f if you can create the def from type, interactionType and moreInfo if the activity already
        # doesn't have a definition
        act_def_created = self.save_activity_definition_to_db(act_def_type, act_def.get('interactionType', ''),
            more_info)

        # If the activity had already existed and lrs auth is off or user has authority to update it
        if not act_created: 
            if self.Activity.authoritative == '' or self.Activity.authoritative == self.auth:
                # Update name and desc if needed
                self.update_activity_name_and_description(act_def)
            else:
                err_msg = "This ActivityID already exists, and you do not have the correct authority to create or update it."
                raise exceptions.Forbidden(err_msg)
        # Else the activity was newly created
        else:
            # If created and have permisson to (re)define activities
            if self.define:
                # Save activity definition names and descriptions
                if 'name' in act_def:
                    for name_lang_map in act_def['name'].items():
                        n = models.ActivityDefinitionNameLangMap.objects.create(key=name_lang_map[0],
                                      value=name_lang_map[1], activity=self.Activity)
                if 'description' in act_def:
                    for desc_lang_map in act_def['description'].items():
                        d = models.ActivityDefinitionDescLangMap.objects.create(key=desc_lang_map[0],
                                      value=desc_lang_map[1], activity=self.Activity)

        # If the activity definition was just created (can't update the CRP or extensions of a def if already existed)
        #If there is a correctResponsesPattern then save the pattern
        if act_def_created and 'correctResponsesPattern' in act_def.keys():
            self.populate_correct_responses_pattern(act_def, interaction_flag)

        #See if activity definition has extensions
        if act_def_created and 'extensions' in act_def.keys():
            self.populate_extensions(act_def) 

    def populate_correct_responses_pattern(self, act_def, interaction_flag):
        #For each answer in the pattern save it
        for i in act_def['correctResponsesPattern']:
            models.CorrectResponsesPatternAnswer.objects.create(answer=i, activity=self.Activity)

        #Depending on which type of interaction, save the unique fields accordingly
        if interaction_flag == 'choices':
            choices = act_def['choices']
            for c in choices:
                choice = models.ActivityDefinitionChoice.objects.create(choice_id=c['id'],
                    activity=self.Activity)
                #Save description as string, not a dictionary
                for desc_lang_map in c['description'].items():
                    lang_map = self.save_lang_map(desc_lang_map, choice, "choice")
        elif interaction_flag == 'scale':
            scales = act_def['scale']
            for s in scales:
                scale = models.ActivityDefinitionScale.objects.create(scale_id=s['id'],
                    activity=self.Activity)        
                # Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    lang_map = self.save_lang_map(desc_lang_map, scale, "scale")
        elif interaction_flag == 'steps':
            steps = act_def['steps']
            for s in steps:
                step = models.ActivityDefinitionStep.objects.create(step_id=s['id'],
                    activity=self.Activity)
                #Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    lang_map = self.save_lang_map(desc_lang_map, step, "step")
        elif interaction_flag == 'source':
            sources = act_def['source'] 
            for s in sources:
                source = models.ActivityDefinitionSource.objects.create(source_id=s['id'],
                    activity=self.Activity)
                #Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    lang_map = self.save_lang_map(desc_lang_map, source, "source")
            targets = act_def['target']
            for t in targets:
                target = models.ActivityDefinitionTarget.objects.create(target_id=t['id'],
                    activity=self.Activity)
                #Save description as string, not a dictionary
                for desc_lang_map in t['description'].items():
                    lang_map = self.save_lang_map(desc_lang_map, target, "target")

    def populate_extensions(self, act_def):
        for k, v in act_def['extensions'].items():
            act_def_ext = models.ActivityDefinitionExtensions.objects.create(key=k, value=v,
                activity=self.Activity)