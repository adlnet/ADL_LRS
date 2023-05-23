import datetime
import json

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.utils.timezone import utc

from ..models import ActivityProfile
from ..exceptions import IDNotFoundError, ParamError, BadRequest
from ..utils import etag


class ActivityProfileManager():

    def save_non_json_profile(self, p, created, profile, request_dict):
        # Save profile content type based on incoming content type header and
        # create etag
        p.content_type = request_dict['headers']['CONTENT_TYPE']
        p.etag = etag.create_tag(profile.read())

        # Set updated
        if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
            p.updated = request_dict['headers']['updated']
        else:
            p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)

        # Go to beginning of file
        profile.seek(0)
        # Set filename with the activityID and profileID and save
        fn = "%s_%s" % (p.activity_id, request_dict.get('filename', p.id))
        p.profile.save(fn, profile)

        p.save()

    def post_profile(self, request_dict):
        # get/create profile
        profile_record, created = ActivityProfile.objects.get_or_create(
            activity_id=request_dict['params']['activityId'],
            profile_id=request_dict['params']['profileId']
        )
        profile_document_contents = request_dict['profile']

        etag.check_modification_conditions(request_dict, profile_record, created, required=True)
        
        # If incoming profile is application/json and if a profile didn't
        # already exist with the same activityId and profileId
        if created:
            profile_record.json_profile = profile_document_contents
            profile_record.content_type = "application/json"
            profile_record.etag = etag.create_tag(profile_document_contents)
        
        elif profile_record.content_type != "application/json":
            raise BadRequest("A matching non-JSON document already exists and cannot be merged or replaced.")
        
        elif "application/json" not in request_dict['headers']['CONTENT_TYPE']:
            raise BadRequest("A non-JSON document cannot be used to update an existing JSON document.")

        # If incoming profile is application/json and if a profile already
        # existed with the same activityId and profileId
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
        # Get the profile, or if not already created, create one
        profile_record, created = ActivityProfile.objects.get_or_create(
            profile_id=request_dict['params']['profileId'], 
            activity_id=request_dict['params']['activityId']
        )
        profile_document_contents = request_dict['profile']

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

            # If a profile already existed with the profileId and activityId
            if not created:
                if profile_record.profile:
                    try:
                        profile_record.profile.delete()
                    except OSError:
                        # probably was json before
                        profile_record.json_profile = {}

            self.save_non_json_profile(profile_record, created, profile, request_dict)
        
        # Profile being PUT is json
        else:
            etag.check_modification_conditions(request_dict, profile_record, created, required=False)
            # If a profile already existed with the profileId and activityId
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

    def get_profile(self, profile_id, activity_id):
        # Retrieve the profile with the given profileId and activity
        try:
            return ActivityProfile.objects.get(profile_id=profile_id, activity_id=activity_id)
        except ActivityProfile.DoesNotExist:
            err_msg = 'There is no activity profile associated with the id: %s' % profile_id
            raise IDNotFoundError(err_msg)

    def get_profile_ids(self, activity_id, since=None):
        ids = []

        # If there is a since param return all profileIds since then
        if since:
            try:
                # this expects iso6801 date/time format
                # "2013-02-15T12:00:00+00:00"
                profs = ActivityProfile.objects.filter(
                    updated__gte=since, activity_id=activity_id)
            except ValidationError:
                err_msg = 'Since field is not in correct format for retrieval of activity profile IDs'
                raise ParamError(err_msg)
            ids = [p.profile_id for p in profs]
        else:
            # Return all IDs of profiles associated with this activity b/c
            # there is no since param
            ids = ActivityProfile.objects.filter(
                activity_id=activity_id).values_list('profile_id', flat=True)
        return ids

    def delete_profile(self, request_dict):
        # Get profile and delete it
        try:
            profile_record = self.get_profile(
                request_dict['params']['profileId'], 
                request_dict['params']['activityId']
            )

            etag.check_modification_conditions(request_dict, profile_record, False, required=True)

            profile_record.delete()
            
        # we don't want it anyway
        except ActivityProfile.DoesNotExist:
            pass
        except IDNotFoundError:
            pass
