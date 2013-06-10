import json
import datetime
from django.core.files.base import ContentFile
from django.db import transaction
from lrs.models import agent_profile
from lrs.models import agent as ag
from lrs.exceptions import IDNotFoundError, ParamError
from lrs.util import etag, get_user_from_auth, uri
import pdb

class Agent():
    @transaction.commit_on_success
    def __init__(self, initial=None, create=False, define=True):
        self.initial = initial
        self.define = define
        params = self.initial

        if not isinstance(params, dict):
            try:
                params = json.loads(self.initial)
            except Exception, e:
                err_msg = "Error parsing the Agent object. Expecting json. Received: %s which is %s" % (self.initial,
                    type(self.initial))
                raise ParamError(err_msg) 

        allowed_fields = ['objectType', 'name', 'member', 'mbox', 'mbox_sha1sum', 'openID', 'account']
        failed_list = [x for x in params.keys() if not x in allowed_fields]
        if failed_list:
            err_msg = "Invalid field(s) found in agent/group %s" % ', '.join(failed_list)
            raise ParamError(err_msg)
        
        if create:
            params['define'] = self.define
            self.agent, created = ag.objects.gen(**params)
        else:
            try:
                if 'member' in params:
                    params.pop('member', None)
                # If retreiving agents always get global version                
                params['global_representation'] = True
                # gotta get account info right for this..
                if 'account' in params:
                    acc = params.pop('account')
                    if 'homePage' in acc:
                        params['agent_account__homePage'] = acc['homePage']
                    if 'name' in acc:
                        params['agent_account__name'] = acc['name']
                self.agent = ag.objects.get(**params)
            except:
                err_msg = "Error with Agent. The agent partial (%s) did not match any agents on record" % self.initial
                raise IDNotFoundError(err_msg) 
        
    def post_profile(self, request_dict):
        post_profile = request_dict['profile']

        profile_id = request_dict['params']['profileId']
        if not uri.validate_uri(profile_id):
            err_msg = 'Profile ID %s is not a valid URI' % profile_id
            raise ParamError(err_msg)

        p, created = agent_profile.objects.get_or_create(profileId=profile_id,agent=self.agent)
        if created:
            profile = ContentFile(post_profile)
        else:
            original_profile = json.load(p.profile)
            post_profile = json.loads(post_profile)
            merged = dict(original_profile.items() + post_profile.items())
            p.profile.delete()
            profile = ContentFile(json.dumps(merged))

        self.save_profile(p, created, profile, request_dict)

    def put_profile(self, request_dict):
        try:
            profile = ContentFile(request_dict['profile'].read())
        except:
            try:
                profile = ContentFile(request_dict['profile'])
            except:
                profile = ContentFile(str(request_dict['profile']))
        
        profile_id = request_dict['params']['profileId']
        if not uri.validate_uri(profile_id):
            err_msg = 'Profile ID %s is not a valid URI' % profile_id
            raise ParamError(err_msg)

        p,created = agent_profile.objects.get_or_create(profileId=profile_id,agent=self.agent)
        if not created:
            etag.check_preconditions(request_dict,p, required=True)
            p.profile.delete()
        self.save_profile(p, created, profile, request_dict)

    def save_profile(self, p, created, profile, request_dict):
        p.content_type = request_dict['headers']['CONTENT_TYPE']
        p.etag = etag.create_tag(profile.read())
        if 'headers' in request_dict and ('updated' in request_dict['headers'] and request_dict['headers']['updated']):
            p.updated = request_dict['headers']['updated']
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
            raise IDNotFoundError(err_msg)

    def get_profile_ids(self, since=None):
        ids = []
        if since:
            try:
                # this expects iso6801 date/time format "2013-02-15T12:00:00+00:00"
                profs = self.agent.agent_profile_set.filter(updated__gte=since)
            except ValidationError:
                err_msg = 'Since field is not in correct format for retrieval of agent profiles'
                raise ParamError(err_msg) 
            except:
                err_msg = 'There are no profiles associated with the id: %s' % profileId
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
