from lrs import models

class ActivityManager():
    def __init__(self, data, auth=None, define=True):
        self.auth = auth
        self.define = define
        self.populate(data)

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
        can_update = False

        # Try to get canonical
        try:
            act = models.Activity.objects.get(activity_id=activity_id, canonical_version=True)
        except models.Activity.DoesNotExist:
            if self.define:
                # If canonical DNE and can define - create canonical
                self.Activity = models.Activity.objects.create(activity_id=activity_id, canonical_version=True,
                    authority=self.auth)
                act_created = True
            else:
                # If canonical DNE and cannot define - try to get local version for that user
                self.Activity, act_created = models.Activity.objects.get_or_create(activity_id=activity_id, canonical_version=False,
                    authority=self.auth)
        # Canonical version already exists
        else:
            # If canonical already exists and have define
            if self.define:
                # Act exists - if it has same auth set it, else create non-canonical version
                if act.authority == self.auth:
                    self.Activity = act
                    act_created = False
                    can_update = True
                elif act.authority.objectType == 'Group' and self.auth in act.authority.member.all():
                    self.Activity = act
                    act_created = False
                    can_update = True
                elif self.auth.objectType == 'Group' and act.authority in self.auth.member.all():
                    self.Activity = act
                    act_created = False
                    can_update = True                                                        
                else:
                    # Not allowed to create global version b/c the activity already exists (could also already have created a non-global act)
                    self.Activity, act_created = models.Activity.objects.get_or_create(activity_id=activity_id,
                        canonical_version=False, authority=self.auth)
            # Canonical version already exists but do not have define - try to get local version for that user or create it for user
            else:
                self.Activity, act_created = models.Activity.objects.get_or_create(activity_id=activity_id,
                    canonical_version=False, authority=self.auth)

        activity_definition = the_object.get('definition', None)

        # If there is a definition-populate the definition
        if activity_definition and (act_created or self.act_def_changed(activity_definition)):
            self.populate_definition(activity_definition, act_created, can_update)

    def act_def_changed(self, act_def):
        return act_def != self.Activity.object_return().get('definition', {})

    #Populate definition either from JSON or validated XML
    def populate_definition(self, act_def, act_created, can_update):
        # return t/f if you can create the def from type, interactionType and moreInfo if the activity already
        # doesn't have a definition
        act_def_created = self.save_activity_definition_to_db(act_def.get('type', ''), act_def.get('interactionType', ''),
            act_def.get('moreInfo', ''), act_def.get('name', {}), act_def.get('description', {}),
            act_def.get('correctResponsesPattern', {}), act_def.get('extensions', {}))

        # If the activity had already existed and lrs auth is off or user has authority to update it
        if not act_created: 
            if not self.Activity.authority or can_update:
                # Update name and desc if needed
                if 'name' in act_def:
                    if self.Activity.activity_definition_name:
                        self.Activity.activity_definition_name = dict(self.Activity.activity_definition_name.items() + act_def['name'].items())
                    else:
                        self.Activity.activity_definition_name = act_def['name']
                    self.Activity.save()

                if 'description' in act_def:
                    if self.Activity.activity_definition_description:
                        self.Activity.activity_definition_description = dict(self.Activity.activity_definition_description.items() + act_def['description'].items())
                    else:
                        self.Activity.activity_definition_description = act_def['description']
                    self.Activity.save()

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