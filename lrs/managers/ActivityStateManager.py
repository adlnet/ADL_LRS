import datetime
import json

from typing import Tuple

from django.core.files.base import ContentFile
from django.utils.timezone import utc

from ..models import ActivityState
from ..exceptions import IDNotFoundError, BadRequest
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

    def get_record(self, **kwargs) -> Tuple[ActivityState, bool]:

        if "registration" in kwargs and kwargs.get("registration", None) is None:
            del kwargs["registration"]

        return ActivityState.objects.get_or_create(**kwargs)


    def get_state_set(self, activity_id, registration, since):
        if registration:
            # Registration and since
            if since:
                state_set = self.Agent.activitystate_set.filter(
                    activity_id=activity_id, registration_id=registration, updated__gt=since)
            # Registration
            else:
                state_set = self.Agent.activitystate_set.filter(activity_id=activity_id, registration_id=registration)
        else:
            # Since
            if since:
                state_set = self.Agent.activitystate_set.filter(activity_id=activity_id, updated__gt=since)
            # Neither
            else:
                state_set = self.Agent.activitystate_set.filter(activity_id=activity_id)
        return state_set

    def post_state(self, request_dict):

        state_record, created = self.get_record(
            state_id=request_dict['params']['stateId'], 
            agent=self.Agent,
            activity_id=request_dict['params']['activityId'],
            registration_id=request_dict['params'].get('registration', None)
        )

        state_document_contents = request_dict['state']

        etag.check_modification_conditions(request_dict, state_record, created, required=True)

        # If incoming state is application/json and if a state didn't
        # already exist with the same agent, stateId, actId, and/or
        # registration
        if created:
            state_record.json_state = state_document_contents
            state_record.content_type = "application/json"
            state_record.etag = etag.create_tag(state_document_contents)
        
        elif state_record.content_type != "application/json":
            raise BadRequest("A matching non-JSON document already exists and cannot be merged or replaced.")
        
        elif "application/json" not in request_dict['headers']['CONTENT_TYPE']:
            raise BadRequest("A non-JSON document cannot be used to update an existing JSON document.")

        # If incoming state is application/json and if a state already
        # existed with the same agent, stateId, actId, and/or registration
        else:
            previous_state_document = json.loads(state_record.json_state)
            updated_state_document = json.loads(state_document_contents)
            
            previous_properties = list(previous_state_document.items())
            updated_properties = list(updated_state_document.items())
            
            merged = json.dumps(dict(previous_properties + updated_properties))
            
            state_record.json_state = merged
            state_record.etag = etag.create_tag(merged)

        # Set updated
        if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
            state_record.updated = request_dict['headers']['updated']
        else:
            state_record.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
        
        state_record.save()

    def put_state(self, request_dict):

        state_record, created = self.get_record(
            state_id=request_dict['params']['stateId'], 
            agent=self.Agent,
            activity_id=request_dict['params']['activityId'],
            registration_id=request_dict['params'].get('registration', None)
        )

        state_document_contents = request_dict['state']

        etag.check_modification_conditions(request_dict, state_record, created, required=True)

        if "application/json" not in request_dict['headers']['CONTENT_TYPE']:
            try:
                state_document_contents = ContentFile(state_document_contents.read())
            except:
                try:
                    state_document_contents = ContentFile(state_document_contents)
                except:
                    state_document_contents = ContentFile(str(state_document_contents))

            # If a state already existed with the profileId and activityId
            if not created:
                if state_record.state:
                    try:
                        state_record.state.delete()
                    except OSError:
                        # probably was json before
                        state_record.json_state = {}
            
            self.save_non_json_state(state_record, state_document_contents, request_dict)
        
        # State being PUT is json
        else:
            the_state = request_dict['state']
            state_record.json_state = the_state
            state_record.content_type = request_dict['headers']['CONTENT_TYPE']
            state_record.etag = etag.create_tag(the_state)

            # Set updated
            if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
                state_record.updated = request_dict['headers']['updated']
            else:
                state_record.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
            
            state_record.save()

    def get_state(self, activity_id, registration, state_id):
        try:
            if registration:
                return self.Agent.activitystate_set.get(state_id=state_id, activity_id=activity_id, registration_id=registration)
            return self.Agent.activitystate_set.get(state_id=state_id, activity_id=activity_id)
        
        except ActivityState.DoesNotExist:
            err_msg = f'There is no activity state associated with the id: {state_id}'
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
