from lrs import models
from lrs.objects.Agent import Agent
from lrs.models import IDNotFoundError
from lrs.util import etag
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from django.db import transaction
import pdb

class ActivityState():
    def __init__(self, request_dict):
        self.req_dict = request_dict
        self.agent = request_dict['agent']
        try:
            self.activity = models.activity.objects.get(activity_id=request_dict['activityId'])
        except models.activity.DoesNotExist:
            raise IDNotFoundError("Error with Activity State. The activity id (%s) did not match any activities on record: %s" % (request_dict['activityId']))
        self.registrationId = request_dict.get('registrationId', None)
        self.stateId = request_dict.get('stateId', None)
        self.updated = request_dict.get('updated', None)
        self.content_type = request_dict.get('CONTENT_TYPE', None)
        self.state = request_dict.get('state', None)
        self.etag = request_dict.get('ETAG', None)
        self.since = request_dict.get('since', None)

    def __get_agent(self, create=False):
        return Agent(self.agent, create).agent

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
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,agent=agent,activity=self.activity,registration_id=self.registrationId)
        else:
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,agent=agent,activity=self.activity)
        if not created:
            etag.check_preconditions(self.req_dict,p)
            p.state.delete() # remove old state file
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
        # pdb.set_trace()
        if not agent.mbox is None:            
            if agent.mbox != auth.email:
                raise ForbiddenException("Unauthorized to retrieve activity state with ID %s" % self.stateId)

        try:
            if self.registrationId:
                return models.activity_state.objects.get(state_id=self.stateId, agent=agent, activity=self.activity, registration_id=self.registrationId)
            return models.activity_state.objects.get(state_id=self.stateId, agent=agent, activity=self.activity)
        except models.activity_state.DoesNotExist:
            raise IDNotFoundError('There is no activity state associated with the id: %s' % self.stateId)

    def get_set(self,auth,**kwargs):
        agent = self.__get_agent()

        if not agent.mbox is None:            
            if agent.mbox != auth.email:
                raise ForbiddenException("Unauthorized to retrieve activity state with ID %s" % self.stateId)

        if self.registrationId:
            state_set = models.activity_state.objects.filter(agent=agent, activity=self.activity, registration_id=self.registrationId)
        else:
            state_set = models.activity_state.objects.filter(agent=agent, activity=self.activity)
        return state_set

    # TODO RETURN NO MATCH
    def get_ids(self, auth):
        try:
            state_set = self.get_set(auth)
        except models.activity_state.DoesNotExist:
            return []
        if self.since:
            state_set = state_set.filter(updated__gte=self.since)
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

class ForbiddenException(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)            