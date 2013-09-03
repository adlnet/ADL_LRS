import json
import urllib2
from StringIO import StringIO
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from lrs import models, exceptions
from lrs.util import uri

class ActivityManager():
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
            act_resp = urllib2.urlopen(req, timeout=5)
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
    def save_activity_definition_to_db(self, act_def_type, int_type, more_info, name, desc, crp, ext):
        created = True        
        # Have to check if the activity already has an activity definition. Can only update name and
        # description in definition, so no matter what the user's scope is, if the activity def already
        # exists you can't create another one
        if (self.Activity.activity_definition_type or self.Activity.activity_definition_moreInfo or
                self.Activity.activity_definition_interactionType):
            created = False
        else:
            self.Activity.activity_definition_name = name
            self.Activity.activity_definition_description = desc
            self.Activity.activity_definition_type = act_def_type
            self.Activity.activity_definition_moreInfo = more_info
            self.Activity.activity_definition_interactionType = int_type
            self.Activity.activity_definition_crpanswers = crp
            self.Activity.activity_definition_extensions = ext
            self.Activity.save()
        return created

    def check_activity_definition_value(self, new_name_value, existing_name_value):
        return new_name_value == existing_name_value

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
        if activity_definition and (act_created or self.act_def_changed(activity_definition)):
            self.populate_definition(activity_definition, act_created)

    def validate_cmi_interaction(self, act_def, act_created):
        interaction_flag = None

        return interaction_flag

    def act_def_changed(self, act_def):
        return act_def != self.Activity.object_return().get('definition', {})

    #Populate definition either from JSON or validated XML
    def populate_definition(self, act_def, act_created):
        # only update existing def stuff if request has authority to do so
        if not act_created and (self.Activity.authoritative != '' and self.Activity.authoritative != self.auth):
            err_msg = "This ActivityID already exists, and you do not have the correct authority to create or update it."
            raise exceptions.Forbidden(err_msg)

        # return t/f if you can create the def from type, interactionType and moreInfo if the activity already
        # doesn't have a definition
        act_def_created = self.save_activity_definition_to_db(act_def.get('type', ''), act_def.get('interactionType', ''),
            act_def.get('moreInfo', ''), act_def.get('name', ''), act_def.get('description', ''),
            act_def.get('correctResponsesPattern', ''), act_def.get('extensions', ''))

        # If the activity had already existed and lrs auth is off or user has authority to update it
        if not act_created: 
            if self.Activity.authoritative == '' or self.Activity.authoritative == self.auth:
                # Update name and desc if needed
                if 'name' in act_def:
                    self.Activity.activity_definition_name = dict(self.Activity.activity_definition_name.items() + act_def['name'].items())
                    self.Activity.save()

                if 'description' in act_def:
                    self.Activity.activity_definition_description = dict(self.Activity.activity_definition_description.items() + act_def['description'].items())
                    self.Activity.save()
            else:
                err_msg = "This ActivityID already exists, and you do not have the correct authority to create or update it."
                raise exceptions.Forbidden(err_msg)

        # If the activity definition was just created (can't update the CRP or extensions of a def if already existed)
        #If there is a correctResponsesPattern then save the pattern
        if act_def_created and self.Activity.activity_definition_crpanswers:
            self.populate_correct_responses_pattern(act_def)

    def populate_correct_responses_pattern(self, act_def):
        #Multiple choice and sequencing must have choices
        if act_def['interactionType'] == 'choice' or \
            act_def['interactionType'] == 'sequencing':
            self.Activity.activity_definition_choices = act_def['choices']
        #Matching must have both source and target
        elif act_def['interactionType'] == 'matching':
            self.Activity.activity_definition_sources = act_def['source'] 
            self.Activity.activity_definition_targets = act_def['target']
        #Performance must have steps
        elif act_def['interactionType'] == 'performance':
            self.Activity.activity_definition_steps = act_def['steps']
        #Likert must have scale
        elif act_def['interactionType'] == 'likert':
            self.Activity.activity_definition_scales = act_def['scale']
        self.Activity.save()