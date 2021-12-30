import datetime
import json

from django.core.files.base import ContentFile
from django.utils.timezone import utc

from ..models import ActivityState
from ..exceptions import IDNotFoundError
from ..utils import etag


class ActivityStateManager():

    def __init__(self, agent):
        self.Agent = agent

    def save_non_json_state(self, s, state, request_dict):
        s.content_type = request_dict['headers']['CONTENT_TYPE']
        s.etag = etag.create_tag(state.read())

        if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
            s.updated = request_dict['headers']['updated']
        else:
            s.updated = datetime.datetime.utcnow().replace(tzinfo=utc)

        # Go to beginning of file
        state.seek(0)
        fn = "%s_%s_%s" % (s.agent_id, s.activity_id,
                           request_dict.get('filename', s.id))
        s.state.save(fn, state)

        s.save()

    def get_state_set(self, activity_id, registration, since):
        if registration:
            # Registration and since
            if since:
                state_set = self.Agent.activitystate_set.filter(
                    activity_id=activity_id, registration_id=registration, updated__gt=since)
            # Registration
            else:
                state_set = self.Agent.activitystate_set.filter(
                    activity_id=activity_id, registration_id=registration)
        else:
            # Since
            if since:
                state_set = self.Agent.activitystate_set.filter(
                    activity_id=activity_id, updated__gt=since)
            # Neither
            else:
                state_set = self.Agent.activitystate_set.filter(
                    activity_id=activity_id)
        return state_set

    def post_state(self, request_dict):
        registration = request_dict['params'].get('registration', None)
        if registration:
            s, created = ActivityState.objects.get_or_create(state_id=request_dict['params']['stateId'], agent=self.Agent,
                                                             activity_id=request_dict['params']['activityId'],
                                                             registration_id=request_dict['params']['registration'])
        else:
            s, created = ActivityState.objects.get_or_create(state_id=request_dict['params']['stateId'], agent=self.Agent,
                                                             activity_id=request_dict['params']['activityId'])
        post_state = request_dict['state']
        # If incoming state is application/json and if a state didn't
        # already exist with the same agent, stateId, actId, and/or
        # registration
        if created:
            s.json_state = post_state
            s.content_type = "application/json"
            s.etag = etag.create_tag(post_state)
        # If incoming state is application/json and if a state already
        # existed with the same agent, stateId, actId, and/or registration
        else:
            orig_state = json.loads(s.json_state)
            post_state = json.loads(post_state)
            merged = json.dumps(
                dict(list(orig_state.items()) + list(post_state.items())))
            s.json_state = merged
            s.etag = etag.create_tag(merged)

            # Set updated
        if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
            s.updated = request_dict['headers']['updated']
        else:
            s.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
        s.save()

    def put_state(self, request_dict):
        registration = request_dict['params'].get('registration', None)
        if registration:
            s, created = ActivityState.objects.get_or_create(state_id=request_dict['params']['stateId'],
                                                             agent=self.Agent,
                                                             activity_id=request_dict['params']['activityId'],
                                                             registration_id=request_dict['params']['registration'])
        else:
            s, created = ActivityState.objects.get_or_create(state_id=request_dict['params']['stateId'],
                                                             agent=self.Agent,
                                                             activity_id=request_dict['params']['activityId'])

        if "application/json" not in request_dict['headers']['CONTENT_TYPE']:
            try:
                post_state = ContentFile(request_dict['state'].read())
            except:
                try:
                    post_state = ContentFile(request_dict['state'])
                except:
                    post_state = ContentFile(str(request_dict['state']))

            etag.check_preconditions(request_dict, s, created, False)
            # If a state already existed with the profileId and activityId
            if not created:
                if s.state:
                    try:
                        s.state.delete()
                    except OSError:
                        # probably was json before
                        s.json_state = {}
            self.save_non_json_state(s, post_state, request_dict)
        # State being PUT is json
        else:
            etag.check_preconditions(request_dict, s, created, False)
            the_state = request_dict['state']
            s.json_state = the_state
            s.content_type = request_dict['headers']['CONTENT_TYPE']
            s.etag = etag.create_tag(the_state)

            # Set updated
            if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
                s.updated = request_dict['headers']['updated']
            else:
                s.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
            s.save()

    def get_state(self, activity_id, registration, state_id):
        try:
            if registration:
                return self.Agent.activitystate_set.get(state_id=state_id, activity_id=activity_id, registration_id=registration)
            return self.Agent.activitystate_set.get(state_id=state_id, activity_id=activity_id)
        except ActivityState.DoesNotExist:
            err_msg = 'There is no activity state associated with the id: %s' % state_id
            raise IDNotFoundError(err_msg)

    def get_state_ids(self, activity_id, registration, since):
        state_set = self.get_state_set(activity_id, registration, since)
        # If state_set isn't empty
        if state_set:
            return state_set.values_list('state_id', flat=True)
        return state_set

    def delete_state(self, request_dict):
        state_id = request_dict['params'].get('stateId', None)
        activity_id = request_dict['params']['activityId']
        registration = request_dict['params'].get('registration', None)
        try:
            # Bulk delete if stateId is not in params
            if not state_id:
                states = self.get_state_set(activity_id, registration, None)
                for s in states:
                    s.delete()  # bulk delete skips the custom delete function
            # Single delete
            else:
                self.get_state(activity_id, registration, state_id).delete()
        except ActivityState.DoesNotExist:
            pass
        except IDNotFoundError:
            pass
