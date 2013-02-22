from lrs import models
from lrs.objects.Agent import Agent
from lrs.exceptions import IDNotFoundError #, Forbidden
from lrs.util import etag, get_user_from_auth, log_message, update_parent_log_status
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from django.db import transaction
import pdb
import logging
import datetime

logger = logging.getLogger('user_system_actions')

class ActivityState():
    def __init__(self, request_dict, log_dict=None):
        self.req_dict = request_dict
        self.log_dict = log_dict
        self.agent = request_dict['agent']
        self.auth = request_dict.get('auth', None)
        self.user = get_user_from_auth(self.auth)
        try:
            self.activity = models.activity.objects.get(activity_id=request_dict['activityId'])
        except models.activity.DoesNotExist:
            err_msg = "Error with Activity State. The activity id (%s) did not match any activities on record" % (request_dict['activityId'])
            log_message(self.log_dict, err_msg, __name__, self.__init__.__name__, True)
            raise IDNotFoundError(err_msg)
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
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,agent=agent,activity=self.activity,registration_id=self.registrationId, user=self.user)
        else:
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,agent=agent,activity=self.activity, user=self.user)
        
        if created:
            log_message(self.log_dict, "Created Activity State", __name__, self.put.__name__)
        elif not created:
            etag.check_preconditions(self.req_dict,p)
            p.state.delete() # remove old state file
            log_message(self.log_dict, "Retrieved Activity State", __name__, self.put.__name__)

        # if not created:
        #     etag.check_preconditions(self.req_dict,p)
        #     p.state.delete() # remove old state file
        p.content_type = self.content_type
        p.etag = etag.create_tag(state.read())
        if self.updated:
            p.updated = self.updated
        state.seek(0)
        if created:
            p.save()

        fn = "%s_%s_%s" % (p.agent_id,p.activity_id, self.req_dict.get('filename', p.id))
        p.state.save(fn, state)

        log_message(self.log_dict, "Saved Activity State", __name__, self.put.__name__)


    def get(self, auth):
        agent = self.__get_agent()
        # if not agent.mbox is None:            
        #     if agent.mbox != auth.email:
        #         raise Forbidden("Unauthorized to retrieve activity state with ID %s" % self.stateId)

        try:
            if self.registrationId:
                return models.activity_state.objects.get(state_id=self.stateId, agent=agent, activity=self.activity, registration_id=self.registrationId)
            return models.activity_state.objects.get(state_id=self.stateId, agent=agent, activity=self.activity)
        except models.activity_state.DoesNotExist:
            err_msg = 'There is no activity state associated with the id: %s' % self.stateId
            log_message(self.log_dict, err_msg, __name__, self.get.__name__, True)
            update_parent_log_status(self.log_dict, 404)
            raise IDNotFoundError(err_msg)

    def get_set(self,auth,**kwargs):
        agent = self.__get_agent()

        # if not agent.mbox is None:            
        #     if agent.mbox != auth.email:
        #         raise Forbidden("Unauthorized to retrieve activity state with ID %s" % self.stateId)

        if self.registrationId:
            state_set = models.activity_state.objects.filter(agent=agent, activity=self.activity, registration_id=self.registrationId)
        else:
            state_set = models.activity_state.objects.filter(agent=agent, activity=self.activity)
        return state_set


    def get_ids(self, auth):
        try:
            state_set = self.get_set(auth)
        except models.activity_state.DoesNotExist:
            err_msg = 'There is no activity state associated with the ID: %s' % self.stateId
            log_message(self.log_dict, err_msg, __name__, self.get_ids.__name__, True)
            update_parent_log_status(self.log_dict, 404)
            raise IDNotFoundError(err_msg)
        if self.since:
            try:
                # this expects iso6801 date/time format "2013-02-15T12:00:00+00:00"
                state_set = state_set.filter(updated__gte=self.since)
            except ValidationError:
                from django.utils import timezone
                since_i = int(float(since))# this handles timestamp like str(time.time())
                since_dt = datetime.datetime.fromtimestamp(since_i).replace(tzinfo=timezone.get_default_timezone())
                state_set = state_set.filter(updated__gte=since_dt)
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
            