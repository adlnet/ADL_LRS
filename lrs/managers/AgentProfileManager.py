import json
import datetime

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.utils.timezone import utc

from ..models import AgentProfile
from ..exceptions import IDNotFoundError, ParamError, BadRequest
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
        profile_record, created = AgentProfile.objects.get_or_create(profile_id=request_dict['params']['profileId'], agent=self.Agent)
        profile_document_contents = request_dict['profile']

        etag.check_modification_conditions(request_dict, profile_record, created, required=True)
        
        # If incoming profile is application/json and if a profile didn't
        # already exist with the same agent and profileId
        if created:
            profile_record.json_profile = profile_document_contents
            profile_record.content_type = "application/json"
            profile_record.etag = etag.create_tag(profile_document_contents)
        
        elif profile_record.content_type != "application/json":
            raise BadRequest("A matching non-JSON document already exists and cannot be merged or replaced.")
        
        elif "application/json" not in request_dict['headers']['CONTENT_TYPE']:
            raise BadRequest("A non-JSON document cannot be used to update an existing JSON document.")

        # If incoming profile is application/json and if a profile already
        # existed with the same agent and profileId
        else:

            previous_profile = json.loads(profile_record.json_profile)
            updated_profile = json.loads(profile_document_contents)

            previous_profile_properties = list(previous_profile.items())
            updated_profile_properties = list(updated_profile.items())

            merged = json.dumps(dict(previous_profile_properties + updated_profile_properties))

            profile_record.json_profile = merged
            profile_record.content_type = request_dict['headers']['CONTENT_TYPE']
            profile_record.etag = etag.create_tag(merged)
        
        # Set updated
        if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
            profile_record.updated = request_dict['headers']['updated']
        else:
            profile_record.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
        
        profile_record.save()

    def put_profile(self, request_dict):
        # get/create profile
        profile_record, created = AgentProfile.objects.get_or_create(profile_id=request_dict['params']['profileId'], agent=self.Agent)

        profile_document_contents = request_dict['state']

        etag.check_modification_conditions(request_dict, profile_record, created, required=True)

        # Profile being PUT is not json
        if "application/json" not in request_dict['headers']['CONTENT_TYPE']:
            try:
                profile = ContentFile(profile_document_contents.read())
            except:
                try:
                    profile = ContentFile(profile_document_contents)
                except:
                    profile = ContentFile(str(profile_document_contents))

            # If it already exists delete it
            if not created:
                if profile_record.profile:
                    try:
                        profile_record.profile.delete()
                    except OSError:
                        # probably was json before
                        profile_record.json_profile = {}
            
            self.save_non_json_profile(profile_record, profile, request_dict)
        
        # Profile being PUT is json
        else:
            # (overwrite existing profile data)
            the_profile = request_dict['profile']
            profile_record.json_profile = the_profile
            profile_record.content_type = request_dict['headers']['CONTENT_TYPE']
            profile_record.etag = etag.create_tag(the_profile)

            # Set updated
            if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
                profile_record.updated = request_dict['headers']['updated']
            else:
                profile_record.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
            
            profile_record.save()

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
