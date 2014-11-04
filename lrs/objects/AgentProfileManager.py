import json
import datetime

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.timezone import utc

from ..models import AgentProfile
from ..exceptions import IDNotFoundError, ParamError
from ..util import etag

class AgentProfileManager():
    def __init__(self, agent):
    	self.Agent = agent

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
    
    def get_profile(self, profile_id):
        try:
            return self.Agent.agentprofile_set.get(profileId=profile_id)
        except:
            err_msg = 'There is no profile associated with the id: %s' % profile_id
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
                err_msg = 'There are no profiles associated with the id'
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