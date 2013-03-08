import json
import datetime
from lrs.models import agent, group, agent_profile
from lrs.exceptions import IDNotFoundError, ParamError
from lrs.util import etag, get_user_from_auth, log_message, update_parent_log_status, convert_to_dict
from django.core.files.base import ContentFile
from django.db import transaction
import pdb
import logging

logger = logging.getLogger('user_system_actions')

class Agent():
    @transaction.commit_on_success
    def __init__(self, initial=None, create=False, log_dict=None):
        self.initial = initial
        self.log_dict = log_dict
        params = self.initial

        if not isinstance(params, dict):
            try:
                params = json.loads(self.initial)
            except Exception, e:
                err_msg = "Error parsing the Agent object. Expecting json. Received: %s which is %s" % (self.initial,
                    type(self.initial))
                log_message(self.log_dict, err_msg, __name__, self.__init__.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg) 
                
        if 'objectType' in params and params['objectType'] == 'Group':
            obj = group
        else:
            obj = agent
        if create:
            self.agent, created = obj.objects.gen(**params)
            if created:
                log_message(self.log_dict, "Created %s in database" % self.agent.objectType, __name__, self.__init__.__name__)
            elif not created:
                log_message(self.log_dict, "Retrieved %s from database" % self.agent.objectType, __name__, self.__init__.__name__)
        else:
            try:
                if 'member' in params:
                    params.pop('member', None)
                self.agent = obj.objects.get(**params)
                log_message(self.log_dict, "Retrieved %s from database" % self.agent.objectType, __name__, self.__init__.__name__)

            except:
                err_msg = "Error with Agent. The agent partial (%s) did not match any agents on record" % self.initial
                log_message(self.log_dict, err_msg, __name__, self.__init__.__name__, True)
                update_parent_log_status(self.log_dict, 404)
                raise IDNotFoundError(err_msg) 
        
    def put_profile(self, request_dict):
        try:
            profile = ContentFile(request_dict['profile'].read())
        except:
            try:
                profile = ContentFile(request_dict['profile'])
            except:
                profile = ContentFile(str(request_dict['profile']))

        user = get_user_from_auth(request_dict.get('auth', None))
        p,created = agent_profile.objects.get_or_create(profileId=request_dict['profileId'],agent=self.agent, user=user)
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
            err_msg = 'There is no profile associated with the id: %s' % profileId
            log_message(self.log_dict, err_msg, __name__, self.get_profile.__name__, True)
            update_parent_log_status(self.log_dict, 404)            
            raise IDNotFoundError(err_msg)

    def get_profile_ids(self, since=None):
        ids = []
        if since:
            try:
                # this expects iso6801 date/time format "2013-02-15T12:00:00+00:00"
                profs = self.agent.agent_profile_set.filter(updated__gte=since)
            except ValidationError:
                from django.utils import timezone
                since_i = int(float(since))# this handles timestamp like str(time.time())
                since_dt = datetime.datetime.fromtimestamp(since_i).replace(tzinfo=timezone.get_default_timezone())
                profs = self.agent.agent_profile_set.filter(updated__gte=since_dt)
            except:
                err_msg = 'There are no profiles associated with the id: %s' % profileId
                log_message(self.log_dict, err_msg, __name__, self.get_profile_ids.__name__, True) 
                update_parent_log_status(self.log_dict, 404)          
                raise IDNotFoundError(err_msg) 

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
