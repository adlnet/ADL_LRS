import json
import datetime
from lrs.models import agent, group, agent_profile, IDNotFoundError
from lrs.util import etag
from django.core.files.base import ContentFile
from django.db import transaction

class Agent():
    @transaction.commit_on_success
    def __init__(self, initial=None, create=False):
        self.initial = initial
        params = self.initial
        if isinstance(params, dict):
            self.initial = json.dumps(self.initial)
        else:
            try:
                params = ast.literal_eval(params)
            except:
                params = json.loads(params)
        
        if 'objectType' in params and params['objectType'] == 'Group':
            obj = group
        else:
            obj = agent
        if create:
            self.agent, created = obj.objects.gen(**params)
        else:
            try:
                if 'member' in params:
                    params.pop('member', None)
                self.agent = obj.objects.get(**params)
            except:
                raise IDNotFoundError("Error with Agent. The agent partial (%s) did not match any agents on record" % self.initial) 
        
    def put_profile(self, request_dict):
        try:
            profile = ContentFile(request_dict['profile'].read())
        except:
            try:
                profile = ContentFile(request_dict['profile'])
            except:
                profile = ContentFile(str(request_dict['profile']))

        p,created = agent_profile.objects.get_or_create(profileId=request_dict['profileId'],agent=self.agent)
        if not created:
            etag.check_preconditions(request_dict,p, required=True)
            p.profile.delete()
        p.content_type = request_dict['CONTENT_TYPE']
        p.etag = etag.create_tag(profile.read())
        if request_dict['updated']:
            p.updated = request_dict['updated']
        profile.seek(0)
        if created:
            p.save()

        fn = "%s_%s" % (p.agent_id,request_dict.get('filename', p.id))
        p.profile.save(fn, profile)
    
    def get_profile(self, profileId):
        try:
            return self.agent.agent_profile_set.get(profileId=profileId)
        except:
            raise IDNotFoundError('There is no profile associated with the id: %s' % profileId)

    def get_profile_ids(self, since=None):
        ids = []
        if since:
            try:
                profs = self.agent.agent_profile_set.filter(updated__gte=since)
            except ValidationError:
                since_i = int(float(since))
                since_dt = datetime.datetime.fromtimestamp(since_i)
                profs = self.agent.agent_profile_set.filter(update__gte=since_dt)
            except:
                raise IDNotFoundError('There are no profiles associated with the id: %s' % profileId)                

            ids = [p.profileId for p in profs]
        else:
            ids = self.agent.agent_profile_set.values_list('profileId', flat=True)
        return ids

    def delete_profile(self, profileId):
        try:
            prof = self.get_profile(profileId)
            prof.delete()
        except agent_profile.DoesNotExist:
            pass #we don't want it anyway
        except IDNotFoundError:
            pass

    def get_agent_json(self):
        return json.dumps(self.agent.get_agent_json(), sort_keys=True)

    def get_person_json(self):
        return json.dumps(self.agent.get_person_json(), sort_keys=True)

class MultipleAgentError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)