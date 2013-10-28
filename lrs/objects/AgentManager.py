import ast
import json
import datetime
import copy
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.timezone import utc
from lrs.models import AgentProfile
from lrs.models import Agent as ag
from lrs.exceptions import IDNotFoundError, ParamError
from lrs.util import etag, get_user_from_auth

class AgentManager():
    def __init__(self, params=None, create=False, define=True):
        self.define = define
        # This parsing is kept for profile/state/agents endpoints
        if not isinstance(params, dict):
            try:
                params = json.loads(params)
            except Exception, e:
                err_msg = "Error parsing the Agent object. Expecting json. Received: %s which is %s" % (params,
                    type(params))
                raise ParamError(err_msg) 
        
        if create:
            params['define'] = self.define
            self.Agent, created = ag.objects.gen(**params)
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
                        params['account_homePage'] = acc['homePage']
                    if 'name' in acc:
                        params['account_name'] = acc['name']
                self.Agent = ag.objects.get(**params)
            except:
                err_msg = "Error with Agent. The agent partial did not match any agents on record"
                raise IDNotFoundError(err_msg) 

    @transaction.commit_on_success        
    def post_profile(self, request_dict):
        post_profile = request_dict['profile']

        profile_id = request_dict['params']['profileId']

        p, created = AgentProfile.objects.get_or_create(profileId=profile_id,agent=self.Agent)
        
        if created:
            p.json_profile = post_profile
            p.content_type = request_dict['headers']['CONTENT_TYPE']
            p.etag = etag.create_tag(post_profile)

            if 'headers' in request_dict and ('updated' in request_dict['headers'] and request_dict['headers']['updated']):
                p.updated = request_dict['headers']['updated']
            else:
                p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
        else:
            etag.check_preconditions(request_dict,p, required=True)
            orig_prof = json.loads(p.json_profile)
            post_profile = json.loads(post_profile)
            if not isinstance(post_profile, dict):
                raise ParamError("The document was not able to be parsed into a JSON object.")
            else:
                merged = json.dumps(dict(orig_prof.items() + post_profile.items()))
            p.json_profile = merged
            p.etag = etag.create_tag(merged)
            p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)

        p.save()

    @transaction.commit_on_success
    def put_profile(self, request_dict):
        profile_id = request_dict['params']['profileId']

        p,created = AgentProfile.objects.get_or_create(profileId=profile_id,agent=self.Agent)

        if "application/json" not in request_dict['headers']['CONTENT_TYPE']:
            try:
                profile = ContentFile(request_dict['profile'].read())
            except:
                try:
                    profile = ContentFile(request_dict['profile'])
                except:
                    profile = ContentFile(str(request_dict['profile']))
        

            if not created:
                etag.check_preconditions(request_dict,p, required=True)
                try:
                    p.profile.delete()
                except OSError:
                    # p was probably json before.. gotta clear that field
                    p.json_profile = {}
            self.save_profile(p, created, profile, request_dict)
        else:
            if not created:
                etag.check_preconditions(request_dict, p, required=True)
            the_profile = request_dict['profile']
            p.json_profile = the_profile
            p.content_type = request_dict['headers']['CONTENT_TYPE']
            p.etag = etag.create_tag(the_profile)

            if 'headers' in request_dict and ('updated' in request_dict['headers'] and request_dict['headers']['updated']):
                p.updated = request_dict['headers']['updated']
            else:
                p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
            p.save()

    def save_profile(self, p, created, profile, request_dict):
        p.content_type = request_dict['headers']['CONTENT_TYPE']
        p.etag = etag.create_tag(profile.read())
        if 'headers' in request_dict and ('updated' in request_dict['headers'] and request_dict['headers']['updated']):
            p.updated = request_dict['headers']['updated']
        else:
            p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
        profile.seek(0)
        if created:
            p.save()

        fn = "%s_%s" % (p.agent_id,request_dict.get('filename', p.id))
        p.profile.save(fn, profile)
    
    def get_profile(self, profileId):
        try:
            return self.Agent.agentprofile_set.get(profileId=profileId)
        except:
            err_msg = 'There is no profile associated with the id: %s' % profileId
            raise IDNotFoundError(err_msg)

    def get_profile_ids(self, since=None):
        ids = []
        if since:
            try:
                # this expects iso6801 date/time format "2013-02-15T12:00:00+00:00"
                profs = self.Agent.agentprofile_set.filter(updated__gte=since)
            except ValidationError:
                err_msg = 'Since field is not in correct format for retrieval of agent profiles'
                raise ParamError(err_msg) 
            except:
                err_msg = 'There are no profiles associated with the id: %s' % profileId
                raise IDNotFoundError(err_msg) 

            ids = [p.profileId for p in profs]
        else:
            ids = self.Agent.agentprofile_set.values_list('profileId', flat=True)
        return ids

    def delete_profile(self, profileId):
        try:
            prof = self.get_profile(profileId)
            prof.delete()
        except AgentProfile.DoesNotExist:
            pass #we don't want it anyway
        except IDNotFoundError:
            pass
        except OSError:
            pass # this is ok,too

    def get_agent_json(self):
        return json.dumps(self.Agent.get_agent_json(), sort_keys=True)

    def get_person_json(self):
        return json.dumps(self.Agent.get_person_json(), sort_keys=True)
