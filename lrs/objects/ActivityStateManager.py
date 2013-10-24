import ast
import datetime
import json
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.timezone import utc
from lrs import models
from .AgentManager import AgentManager
from lrs.exceptions import IDNotFoundError, ParamError
from lrs.util import etag, get_user_from_auth, uri

class ActivityStateManager():
    def __init__(self, request_dict, log_dict=None):        
        if not uri.validate_uri(request_dict['params']['activityId']):
            err_msg = 'Activity ID %s is not a valid URI' % request_dict['params']['activityId']       
            raise exceptions.ParamError(err_msg)

        self.req_dict = request_dict
        self.agent = request_dict['params']['agent']
        self.activity_id = request_dict['params']['activityId']
        self.registration = request_dict['params'].get('registration', None)
        self.stateId = request_dict['params'].get('stateId', None)
        self.updated = request_dict['headers'].get('updated', None)
        self.content_type = request_dict['headers'].get('CONTENT_TYPE', None)
        self.state = request_dict.get('state', None)
        self.etag = request_dict.get('ETAG', None)
        self.since = request_dict['params'].get('since', None)

    def __get_agent(self, create=False):
        # import pdb
        # pdb.set_trace()
        return AgentManager(self.agent, create).Agent

    @transaction.commit_on_success
    def post(self):
        agent = self.__get_agent(create=True)
        post_state = self.state
        if self.registration:
            p,created = models.ActivityState.objects.get_or_create(state_id=self.stateId,agent=agent,activity_id=self.activity_id,registration_id=self.registration)
        else:
            p,created = models.ActivityState.objects.get_or_create(state_id=self.stateId,agent=agent,activity_id=self.activity_id)
        
        if created:
            p.json_state = post_state
            p.content_type = self.content_type
            p.etag = etag.create_tag(post_state)

            if self.updated:
                p.updated = self.updated
        else:
            orig_state = json.loads(p.json_state)
            post_state = json.loads(post_state)
            if not isinstance(post_state, dict):
                raise ParamError("The document was not able to be parsed into a JSON object.")
            else:
                merged = json.dumps(dict(orig_state.items() + post_state.items()))
            p.json_state = merged
            p.etag = etag.create_tag(merged)
            p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)

        p.save()
        
    @transaction.commit_on_success
    def put(self):
        agent = self.__get_agent(create=True)
        if self.registration:
            p,created = models.ActivityState.objects.get_or_create(state_id=self.stateId,agent=agent,activity_id=self.activity_id,registration_id=self.registration)
        else:
            p,created = models.ActivityState.objects.get_or_create(state_id=self.stateId,agent=agent,activity_id=self.activity_id)
        
        if "application/json" not in self.content_type:
            try:
                state = ContentFile(self.state.read())
            except:
                try:
                    state = ContentFile(self.state)
                except:
                    state = ContentFile(str(self.state))

            if not created:
                etag.check_preconditions(self.req_dict,p)
                p.state.delete() # remove old state file
            self.save_state(p, created, state)
        else:
            if not created:
                etag.check_preconditions(self.req_dict, p)
            the_state = self.state
            p.json_state = the_state
            p.content_type = self.content_type
            p.etag = etag.create_tag(the_state)
            if self.updated:
                p.updated = self.updated
            else:
                p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
            p.save()

    def save_state(self, p, created, state):
        p.content_type = self.content_type
        p.etag = etag.create_tag(state.read())
        if self.updated:
            p.updated = self.updated
        else:
            p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
        state.seek(0)
        if created:
            p.save()

        fn = "%s_%s_%s" % (p.agent_id,p.activity_id, self.req_dict.get('filename', p.id))
        p.state.save(fn, state)

    def get(self):
        agent = self.__get_agent()
        try:
            if self.registration:
                return models.ActivityState.objects.get(state_id=self.stateId, agent=agent, activity_id=self.activity_id, registration_id=self.registration)
            return models.ActivityState.objects.get(state_id=self.stateId, agent=agent, activity_id=self.activity_id)
        except models.ActivityState.DoesNotExist:
            err_msg = 'There is no activity state associated with the id: %s' % self.stateId
            raise IDNotFoundError(err_msg)

    def get_set(self,**kwargs):
        agent = self.__get_agent()
        if self.registration:
            state_set = models.ActivityState.objects.filter(agent=agent, activity_id=self.activity_id, registration_id=self.registration)
        else:
            state_set = models.ActivityState.objects.filter(agent=agent, activity_id=self.activity_id)
        return state_set


    def get_ids(self):
        try:
            state_set = self.get_set()
        except models.ActivityState.DoesNotExist:
            err_msg = 'There is no activity state associated with the ID: %s' % self.stateId
            raise IDNotFoundError(err_msg)
        if self.since:
            try:
                # this expects iso6801 date/time format "2013-02-15T12:00:00+00:00"
                state_set = state_set.filter(updated__gte=self.since)
            except ValidationError:
                err_msg = 'Since field is not in correct format for retrieval of state IDs'
                raise ParamError(err_msg) 
        return state_set.values_list('state_id', flat=True)

    def delete(self):
        try:
            if not self.stateId:
                state = self.get_set()
                for s in state:
                    s.delete() # bulk delete skips the custom delete function
            else:
                state = self.get()
                state.delete()
        except models.ActivityState.DoesNotExist:
            pass
        except IDNotFoundError:
            pass
            