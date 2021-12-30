import json
import datetime

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.utils.timezone import utc

from ..models import AgentProfile
from ..exceptions import IDNotFoundError, ParamError
from ..utils import etag


class AgentProfileManager():

    def __init__(self, agent):
        self.Agent = agent

    def save_non_json_profile(self, p, profile, request_dict):
        p.content_type = request_dict['headers']['CONTENT_TYPE']
        p.etag = etag.create_tag(profile.read())

        if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
            p.updated = request_dict['headers']['updated']
        else:
            p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
        # Go to beginning of file
        profile.seek(0)
        fn = "%s_%s" % (p.agent_id, request_dict.get('filename', p.id))
        p.profile.save(fn, profile)
        p.save()

    def post_profile(self, request_dict):
        # get/create profile
        p, created = AgentProfile.objects.get_or_create(
            profile_id=request_dict['params']['profileId'], agent=self.Agent)

        post_profile = request_dict['profile']
        # If incoming profile is application/json and if a profile didn't
        # already exist with the same agent and profileId
        if created:
            p.json_profile = post_profile
            p.content_type = "application/json"
            p.etag = etag.create_tag(post_profile)
        # If incoming profile is application/json and if a profile already
        # existed with the same agent and profileId
        else:
            orig_prof = json.loads(p.json_profile)
            post_profile = json.loads(post_profile)
            merged = json.dumps(
                dict(list(orig_prof.items()) + list(post_profile.items())))
            p.json_profile = merged
            p.etag = etag.create_tag(merged)

        # Set updated
        if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
            p.updated = request_dict['headers']['updated']
        else:
            p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
        p.save()

    def put_profile(self, request_dict):
        # get/create profile
        p, created = AgentProfile.objects.get_or_create(
            profile_id=request_dict['params']['profileId'], agent=self.Agent)

        # Profile being PUT is not json
        if "application/json" not in request_dict['headers']['CONTENT_TYPE']:
            try:
                profile = ContentFile(request_dict['profile'].read())
            except:
                try:
                    profile = ContentFile(request_dict['profile'])
                except:
                    profile = ContentFile(str(request_dict['profile']))

            etag.check_preconditions(request_dict, p, created)
            # If it already exists delete it
            if p.profile:
                try:
                    p.profile.delete()
                except OSError:
                    # probably was json before
                    p.json_profile = {}
            self.save_non_json_profile(p, profile, request_dict)
        # Profile being PUT is json
        else:
            # (overwrite existing profile data)
            etag.check_preconditions(request_dict, p, created)
            the_profile = request_dict['profile']
            p.json_profile = the_profile
            p.content_type = request_dict['headers']['CONTENT_TYPE']
            p.etag = etag.create_tag(the_profile)

            # Set updated
            if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
                p.updated = request_dict['headers']['updated']
            else:
                p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
            p.save()

    def get_profile(self, profile_id):
        try:
            return self.Agent.agentprofile_set.get(profile_id=profile_id)
        except:
            err_msg = 'There is no agent profile associated with the id: %s' % profile_id
            raise IDNotFoundError(err_msg)

    def get_profile_ids(self, since=None):
        ids = []
        if since:
            try:
                # this expects iso6801 date/time format
                # "2013-02-15T12:00:00+00:00"
                profs = self.Agent.agentprofile_set.filter(updated__gt=since)
            except ValidationError:
                err_msg = 'Since field is not in correct format for retrieval of agent profiles'
                raise ParamError(err_msg)
            ids = [p.profile_id for p in profs]
        else:
            ids = self.Agent.agentprofile_set.values_list(
                'profile_id', flat=True)
        return ids

    def delete_profile(self, profile_id):
        try:
            self.get_profile(profile_id).delete()
        # we don't want it anyway
        except AgentProfile.DoesNotExist:
            pass
        except IDNotFoundError:
            pass
