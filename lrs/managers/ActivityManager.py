from django.db import IntegrityError

from ..models import Activity


class ActivityManager():

    def __init__(self, data, auth=None, define=True):
        self.auth = auth
        self.define_permission = define
        self.activity = None
        self.populate(data)

    def update_language_maps(self, incoming_act_def):
        # If there was no definition in the canonical data, and there is an
        # incoming one, set it to incoming data
        if 'definition' not in self.activity.canonical_data and incoming_act_def:
            self.activity.canonical_data['definition'] = incoming_act_def
        # Else there was existing canonical data, and there in an incoming one,
        # only update lang maps (name, desc, interaction activities)
        elif 'definition' in self.activity.canonical_data and incoming_act_def:
            if 'name' not in incoming_act_def:
                incoming_act_def['name'] = {}
            if 'name' not in self.activity.canonical_data['definition']:
                self.activity.canonical_data['definition']['name'] = {}
            if 'description' not in incoming_act_def:
                incoming_act_def['description'] = {}
            if 'description' not in self.activity.canonical_data['definition']:
                self.activity.canonical_data['definition']['description'] = {}

            self.activity.canonical_data['definition']['name'] = dict(list(self.activity.canonical_data['definition']['name'].items()) +
                                                                      list(incoming_act_def['name'].items()))
            self.activity.canonical_data['definition']['description'] = dict(list(self.activity.canonical_data['definition']['description'].items()) +
                                                                             list(incoming_act_def['description'].items()))
            if 'scale' in incoming_act_def and 'scale' in self.activity.canonical_data['definition']:
                trans = {x['id']: x['description']
                         for x in incoming_act_def['scale']}
                for s in self.activity.canonical_data['definition']['scale']:
                    if s['id'] in trans:
                        s['description'] = dict(
                            list(s['description'].items()) + list(trans[s['id']].items()))
            if 'choices' in incoming_act_def and 'choices' in self.activity.canonical_data['definition']:
                trans = {x['id']: x['description']
                         for x in incoming_act_def['choices']}
                for c in self.activity.canonical_data['definition']['choices']:
                    if c['id'] in trans:
                        c['description'] = dict(
                            list(c['description'].items()) + list(trans[c['id']].items()))
            if 'steps' in incoming_act_def and 'steps' in self.activity.canonical_data['definition']:
                trans = {x['id']: x['description']
                         for x in incoming_act_def['steps']}
                for s in self.activity.canonical_data['definition']['steps']:
                    if s['id'] in trans:
                        s['description'] = dict(
                            list(s['description'].items()) + list(trans[s['id']].items()))
            if 'source' in incoming_act_def and 'source' in self.activity.canonical_data['definition']:
                trans = {x['id']: x['description']
                         for x in incoming_act_def['source']}
                for s in self.activity.canonical_data['definition']['source']:
                    if s['id'] in trans:
                        s['description'] = dict(
                            list(s['description'].items()) + list(trans[s['id']].items()))
            if 'target' in incoming_act_def and 'target' in self.activity.canonical_data['definition']:
                trans = {x['id']: x['description']
                         for x in incoming_act_def['target']}
                for s in self.activity.canonical_data['definition']['target']:
                    if s['id'] in trans:
                        s['description'] = dict(
                            list(s['description'].items()) + list(trans[s['id']].items()))

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
                    # Using get or create inside try for racing issue
                    self.activity, act_created = Activity.objects.get_or_create(
                        activity_id=activity_id, authority=self.auth)
                except IntegrityError:
                    self.activity = Activity.objects.get(
                        activity_id=activity_id)
                    act_created = False
            # If activity DNE and cannot define - create activity without auth
            else:
                try:
                    # Using get or create inside try for racing issue
                    self.activity, act_created = Activity.objects.get_or_create(
                        activity_id=activity_id)
                except IntegrityError:
                    self.activity = Activity.objects.get(
                        activity_id=activity_id)
                    act_created = False
            # If you retrieved an activity that has no auth but user has define
            # permissions, user becomes authority over activity
            if not act_created and can_define and not self.activity.authority:
                self.activity.authority = self.auth
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
        # Set id and objectType regardless
        self.activity.canonical_data['id'] = activity_id
        self.activity.canonical_data['objectType'] = 'Activity'
        incoming_act_def = data.get('definition', None)
        # If activity existed, and the user has define privileges - update
        # activity
        if can_define and not act_created:
            self.update_language_maps(incoming_act_def)
        # If activity was created and the user has define privileges
        elif can_define and act_created:
            # If there is an incoming definition
            if incoming_act_def:
                self.activity.canonical_data['definition'] = incoming_act_def
        self.activity.save()
