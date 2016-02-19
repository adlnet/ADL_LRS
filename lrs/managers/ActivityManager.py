from django.db import IntegrityError

from ..models import Activity

class ActivityManager():
    def __init__(self, data, auth=None, define=True):
        self.auth = auth
        self.define_permission = define
        self.activity = None
        self.populate(data)

    def populate(self, data):
        activity_id = data['id']
        can_define = False
        # Try to get activity
        try:
            self.activity = Activity.objects.get(activity_id=activity_id)
            act_created = False
        # Activity DNE
        except Activity.DoesNotExist:
            # If activity DNE and can define - create activity with auth
            if self.define_permission:
                can_define = True
                try:
                    # Using get or create instead of just create for racing issue
                    self.activity, act_created = Activity.objects.get_or_create(activity_id=activity_id, authority=self.auth)       
                except IntegrityError:
                    self.activity = Activity.objects.get(activity_id=activity_id)
                    act_created = False
            # If activity DNE and cannot define - create activity without auth
            else:
                try:
                    # Using get or create instead of just create for racing issue
                    self.activity, act_created = Activity.objects.get_or_create(activity_id=activity_id)
                except IntegrityError:
                    self.activity = Activity.objects.get(activity_id=activity_id)
                    act_created = False
            # If you retrieved an activity that has no auth but user has define permissions, user becomes authority over activity
            if not act_created and can_define and not self.activity.authority:
                self.activity.authority = self.auth
                self.activity.save()
            # At least populate id and objectType when created even if user has no define permission
            # if act_created:
            #     self.activity.canonical_data['id'] = activity_id
            #     self.activity.canonical_data['objectType'] = 'Activity'
            #     self.activity.save()
        # Activity already exists
        else:
            # If activity already exists and have define
            if self.define_permission:
                # Act exists but it was created by someone who didn't have define permissions so it's up for grabs
                # for first user with define permission or...
                # Act exists - if it has same auth set it, else do nothing    
                if (not self.activity.authority) or \
                   (self.activity.authority == self.auth) or \
                   (self.activity.authority.objectType == 'Group' and self.auth in self.activity.authority.member.all()) or \
                   (self.auth.objectType == 'Group' and self.activity.authority in self.auth.member.all()):
                    can_define = True
                else:
                    can_define = False
            # activity already exists but do not have define
            else:
                can_define = False

        
        incoming_act_def = data.get('definition', None)
        # If activity existed, and the user has define privileges - update activity
        if can_define and not act_created:
            # If there was no definition in the canonical data, and there is an incoming one, set it to incoming data
            if not 'definition' in self.activity.canonical_data and incoming_act_def:
                self.activity.canonical_data['definition'] = incoming_act_def
            # Else there was existing canonical data, and there in an incoming one, only update lang maps (name, desc, interaction activities)
            elif 'definition' in self.activity.canonical_data and incoming_act_def:
                if not 'name' in self.activity.canonical_data['definition']:
                    self.activity.canonical_data['definition']['name'] = {}
                if not 'description' in self.activity.canonical_data['definition']:
                    self.activity.canonical_data['definition']['description'] = {}
                self.activity.canonical_data['definition']['name'] = dict(self.activity.canonical_data['definition']['name'].items() \
                    + incoming_act_def['name'].items())
                self.activity.canonical_data['definition']['description'] = dict(self.activity.canonical_data['definition']['description'].items() \
                    + incoming_act_def['description'].items())
        # If activity was created and the user has define privileges
        elif can_define and act_created:
            # If there is an incoming definition
            if incoming_act_def:
                self.activity.canonical_data['definition'] = incoming_act_def
            self.activity.canonical_data['id'] = activity_id
            self.activity.canonical_data['objectType'] = 'Activity'

        self.activity.save()