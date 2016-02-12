from django.db import IntegrityError

from ..models import Activity

class ActivityManager():
    def __init__(self, data, auth=None, define=True):
        self.auth = auth
        self.define_permission = define
        self.populate(data)

    def create_activity_definition(self, act_def):
        interactionType = act_def.get('interactionType', '')
        self.Activity.activity_definition_name = act_def.get('name', {})
        self.Activity.activity_definition_description = act_def.get('description', {})
        self.Activity.activity_definition_type = act_def.get('type', '')
        self.Activity.activity_definition_moreInfo = act_def.get('moreInfo', '')
        self.Activity.activity_definition_crpanswers = act_def.get('correctResponsesPattern', [])
        self.Activity.activity_definition_extensions = act_def.get('extensions', {})
        self.Activity.activity_definition_interactionType = interactionType

        #Multiple choice and sequencing must have choices
        if (interactionType == 'choice' or \
            interactionType == 'sequencing') and \
            ('choices' in act_def):
            self.Activity.activity_definition_choices = act_def['choices']
        #Matching must have both source and target
        elif (interactionType == 'matching') and \
            ('source' in act_def and 'target' in act_def):
            self.Activity.activity_definition_sources = act_def['source'] 
            self.Activity.activity_definition_targets = act_def['target']
        #Performance must have steps
        elif (interactionType == 'performance') and \
            ('steps' in act_def):
            self.Activity.activity_definition_steps = act_def['steps']
        #Likert must have scale
        elif (interactionType == 'likert') and \
            ('scale' in act_def):
            self.Activity.activity_definition_scales = act_def['scale']
        self.Activity.save()

    def update_activity_definition(self, act_def):
        if 'name' in act_def:
            if self.Activity.activity_definition_name:
                self.Activity.activity_definition_name = dict(self.Activity.activity_definition_name.items() + act_def['name'].items())
            else:
                self.Activity.activity_definition_name = act_def['name']       

        if 'description' in act_def:
            if self.Activity.activity_definition_description:
                self.Activity.activity_definition_description = dict(self.Activity.activity_definition_description.items() + act_def['description'].items())
            else:
                self.Activity.activity_definition_description = act_def['description']
        self.Activity.save()

    def populate(self, the_object):
        activity_id = the_object['id']
        can_define = False
        # Try to get activity
        try:
            act = Activity.objects.get(activity_id=activity_id)
        except Activity.DoesNotExist:
            if self.define_permission:
                can_define = True
                # If activity DNE and can define - create activity with auth
                try:
                    self.Activity, act_created = Activity.objects.get_or_create(activity_id=activity_id, authority=self.auth)       
                except IntegrityError:
                    self.Activity = Activity.objects.get(activity_id=activity_id, authority=self.auth)
                    act_created = False
            else:
                # If activity DNE and cannot define - create activity without auth
                try:
                    self.Activity, act_created = Activity.objects.get_or_create(activity_id=activity_id)
                except IntegrityError:
                    self.Activity = Activity.objects.get(activity_id=activity_id)
                    act_created = False
        # activity already exists
        else:
            self.Activity = act
            act_created = False
            # If activity already exists and have define
            if self.define_permission:
                # Act exists but it was created by someone who didn't have define permissions so it's up for grabs
                # for first user with define permission or...
                # Act exists - if it has same auth set it, else do nothing    
                if (not act.authority) or \
                   (act.authority == self.auth) or \
                   (act.authority.objectType == 'Group' and self.auth in act.authority.member.all()) or \
                   (self.auth.objectType == 'Group' and act.authority in self.auth.member.all()):
                    can_define = True
                else:
                    can_define = False
            # activity already exists but do not have define
            else:
                can_define = False

        activity_definition = the_object.get('definition', None)
        # If there is an incoming definition for an activity that had already existed, and the user has define privelages
        if activity_definition and can_define and not act_created:
            self.update_activity_definition(activity_definition)
        # If there is an incoming definition for an activity and the activity didn't exist yet and the user can update create the definition
        elif activity_definition and can_define and act_created:
            self.create_activity_definition(activity_definition)