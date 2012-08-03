from lrs import models
from lrs.util import etag
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from django.db import transaction
from Actor import Actor, IDNotFoundError

class ActivityState():
    def __init__(self, request_dict):
        self.req_dict = request_dict
        self.actor = request_dict['actor']
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

    def __get_actor(self, create=False):
        actor = Actor(self.actor, create=create).agent
        if not actor:
            raise IDNotFoundError("Error with Activity State. The actor partial (%s) did not match any actors on record" % actor) 
        return actor

    @transaction.commit_on_success
    def put(self):
        actor = self.__get_actor(create=True)
        try:
            state = ContentFile(self.state.read())
        except:
            try:
                state = ContentFile(self.state)
            except:
                state = ContentFile(str(self.state))

        if self.registrationId:
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,actor=actor,activity=self.activity,registration_id=self.registrationId)
        else:
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,actor=actor,activity=self.activity)
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

        fn = "%s_%s_%s" % (p.actor_id,p.activity_id, self.req_dict.get('filename', p.id))
        p.state.save(fn, state)

    def get(self):
        actor = self.__get_actor()
        try:
            if self.registrationId:
                return models.activity_state.objects.get(state_id=self.stateId, actor=actor, activity=self.activity, registration_id=self.registrationId)
            return models.activity_state.objects.get(state_id=self.stateId, actor=actor, activity=self.activity)
        except models.activity_state.DoesNotExist:
            raise IDNotFoundError('There is no activity state associated with the id: %s' % self.stateId)

    def get_set(self,**kwargs):
        actor = self.__get_actor()
        if self.registrationId:
            state_set = models.activity_state.objects.filter(actor=actor, activity=self.activity, registration_id=self.registrationId)
        else:
            state_set = models.activity_state.objects.filter(actor=actor, activity=self.activity)
        return state_set

    def get_ids(self):
        try:
            state_set = self.get_set()
        except models.activity_state.DoesNotExist:
            return []
        if self.since:
            state_set = state_set.filter(updated__gte=self.since)
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
        except models.activity_state.DoesNotExist:
            pass
        except IDNotFoundError:
            pass