import datetime
from django.core.files.base import ContentFile
from django.db import transaction
from lrs import models
from lrs.objects.Agent import Agent
from lrs.exceptions import IDNotFoundError, ParamError
from lrs.util import etag, get_user_from_auth, uri
import pdb
import json

class ActivityState():
    def __init__(self, request_dict):       
        if not uri.validate_uri(request_dict['activityId']):
            err_msg = 'Activity ID %s is not a valid URI' % request_dict['activityId']
            raise exceptions.ParamError(err_msg)

        self.req_dict = request_dict
        self.agent = request_dict['agent']
        self.auth = request_dict.get('auth', None)
        self.user = get_user_from_auth(self.auth)
        self.activity_id = request_dict['activityId']
        self.registrationId = request_dict.get('registrationId', None)
        self.stateId = request_dict.get('stateId', None)
        self.updated = request_dict.get('updated', None)
        self.content_type = request_dict.get('CONTENT_TYPE', None)
        self.state = request_dict.get('state', None)
        self.etag = request_dict.get('ETAG', None)
        self.since = request_dict.get('since', None)

    def __get_agent(self, create=False):
        return Agent(self.agent, create).agent

    def post(self):
        agent = self.__get_agent(create=True)
        post_state = self.state
        if self.registrationId:
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,agent=agent,activity_id=self.activity_id,registration_id=self.registrationId, user=self.user)
        else:
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,agent=agent,activity_id=self.activity_id, user=self.user)
        
        if created:
            state = ContentFile(post_state)
        else:
            original_state = json.load(p.state)
            post_state = json.loads(post_state)
            merged = dict(original_state.items() + post_state.items())
            p.state.delete()
            state = ContentFile(json.dumps(merged))

        self.save_state(p, created, state)

    @transaction.commit_on_success
    def put(self):
        agent = self.__get_agent(create=True)
        try:
            state = ContentFile(self.state.read())
        except:
            try:
                state = ContentFile(self.state)
            except:
                state = ContentFile(str(self.state))

        if self.registrationId:
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,agent=agent,activity_id=self.activity_id,registration_id=self.registrationId, user=self.user)
        else:
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,agent=agent,activity_id=self.activity_id, user=self.user)
        
        if not created:
            etag.check_preconditions(self.req_dict,p)
            p.state.delete() # remove old state file
        self.save_state(p, created, state)

    def save_state(self, p, created, state):
        p.content_type = self.content_type
        p.etag = etag.create_tag(state.read())
        if self.updated:
            p.updated = self.updated
        state.seek(0)
        if created:
            p.save()

        fn = "%s_%s_%s" % (p.agent_id,p.activity_id, self.req_dict.get('filename', p.id))
        p.state.save(fn, state)

    def get(self, auth):
        agent = self.__get_agent()
        try:
            if self.registrationId:
                return models.activity_state.objects.get(state_id=self.stateId, agent=agent, activity_id=self.activity_id, registration_id=self.registrationId)
            return models.activity_state.objects.get(state_id=self.stateId, agent=agent, activity_id=self.activity_id)
        except models.activity_state.DoesNotExist:
            err_msg = 'There is no activity state associated with the id: %s' % self.stateId
            raise IDNotFoundError(err_msg)

    def get_set(self,auth,**kwargs):
        agent = self.__get_agent()
        if self.registrationId:
            state_set = models.activity_state.objects.filter(agent=agent, activity_id=self.activity_id, registration_id=self.registrationId)
        else:
            state_set = models.activity_state.objects.filter(agent=agent, activity_id=self.activity_id)
        return state_set


    def get_ids(self, auth):
        try:
            state_set = self.get_set(auth)
        except models.activity_state.DoesNotExist:
            err_msg = 'There is no activity state associated with the ID: %s' % self.stateId
            raise IDNotFoundError(err_msg)
        if self.since:
            try:
                # this expects iso6801 date/time format "2013-02-15T12:00:00+00:00"
                state_set = state_set.filter(updated__gte=self.since)
            except ValidationError:
                err_msg = 'Since field is not in correct format'
                raise ParamError(err_msg) 
        return state_set.values_list('state_id', flat=True)

    def delete(self, auth):
        try:
            if not self.stateId:
                state = self.get_set(auth)
                for s in state:
                    s.delete() # bulk delete skips the custom delete function
            else:
                state = self.get(auth)
                state.delete()
        except models.activity_state.DoesNotExist:
            pass
        except IDNotFoundError:
            pass
            