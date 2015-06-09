import datetime
import json

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.timezone import utc

from ..models import ActivityProfile
from ..exceptions import IDNotFoundError, ParamError
from ..util import etag

class ActivityProfileManager():
    
    @transaction.commit_on_success
    def save_non_json_profile(self, p, created, profile, request_dict):
        #Save profile content type based on incoming content type header and create etag
        p.content_type = request_dict['headers']['CONTENT_TYPE']
        p.etag = etag.create_tag(profile.read())
        
        #Set updated
        if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
            p.updated = request_dict['headers']['updated']
        else:
            p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)

        #Go to beginning of file
        profile.seek(0)
        #Set filename with the activityID and profileID and save
        fn = "%s_%s" % (p.activityId,request_dict.get('filename', p.id))
        p.profile.save(fn, profile)
        
        p.save()

    @transaction.commit_on_success
    def post_profile(self, request_dict):
        # get/create profile
        p, created = ActivityProfile.objects.get_or_create(activityId=request_dict['params']['activityId'],  profileId=request_dict['params']['profileId'])
        
        if "application/json" not in request_dict['headers']['CONTENT_TYPE']:
            try:
                post_profile = ContentFile(request_dict['profile'].read())
            except:
                try:
                    post_profile = ContentFile(request_dict['profile'])
                except:
                    post_profile = ContentFile(str(request_dict['profile']))            
            self.save_non_json_profile(p, created, post_profile, request_dict)
        else:
            post_profile = request_dict['profile']
            # If incoming profile is application/json and if a profile didn't already exist with the same activityId and profileId
            if created:
                p.json_profile = post_profile
                p.content_type = request_dict['headers']['CONTENT_TYPE']
                p.etag = etag.create_tag(post_profile)
            # If incoming profile is application/json and if a profile already existed with the same activityId and profileId 
            else:
                orig_prof = json.loads(p.json_profile)
                post_profile = json.loads(request_dict['profile'])
                if not isinstance(post_profile, dict):
                    raise ParamError("The document was not able to be parsed into a JSON object.")
                else:
                    # json.dumps changes the format of the string rep of the dict
                    merged = json.dumps(dict(orig_prof.items() + post_profile.items()))
                p.json_profile = merged
                p.etag = etag.create_tag(merged)
            
            #Set updated
            if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
                p.updated = request_dict['headers']['updated']
            else:
                p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
            p.save()

    @transaction.commit_on_success
	#Save profile to desired activity
    def put_profile(self, request_dict):        
        #Get the profile, or if not already created, create one
        p,created = ActivityProfile.objects.get_or_create(profileId=request_dict['params']['profileId'],activityId=request_dict['params']['activityId'])
        
        # Profile being PUT is not json
        if "application/json" not in request_dict['headers']['CONTENT_TYPE']:
            try:
                profile = ContentFile(request_dict['profile'].read())
            except:
                try:
                    profile = ContentFile(request_dict['profile'])
                except:
                    profile = ContentFile(str(request_dict['profile']))

            # If a profile already existed with the profileId and activityId
            if not created:
                #If it already exists delete it
                etag.check_preconditions(request_dict,p, required=True)
                if p.profile:
                    try:
                        p.profile.delete()
                    except OSError:
                        # probably was json before
                        p.json_profile = {}
            
            self.save_non_json_profile(p, created, profile, request_dict)
        # Profile being PUT is json
        else:
            # If a profile already existed with the profileId and activityId (overwrite existing profile data)
            if not created:
                etag.check_preconditions(request_dict, p, required=True)
            the_profile = request_dict['profile']
            p.json_profile = the_profile
            p.content_type = request_dict['headers']['CONTENT_TYPE']
            p.etag = etag.create_tag(the_profile)
            
            #Set updated
            if 'updated' in request_dict['headers'] and request_dict['headers']['updated']:
                p.updated = request_dict['headers']['updated']
            else:
                p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
            p.save()

    def get_profile(self, profileId, activityId):
        #Retrieve the profile with the given profileId and activity
        try:
            return ActivityProfile.objects.get(profileId=profileId, activityId=activityId)
        except ActivityProfile.DoesNotExist:
            err_msg = 'There is no activity profile associated with the id: %s' % profileId
            raise IDNotFoundError(err_msg)

    def get_profile_ids(self, activityId, since=None):
        ids = []

        #If there is a since param return all profileIds since then
        if since:
            try:
                # this expects iso6801 date/time format "2013-02-15T12:00:00+00:00"
                profs = ActivityProfile.objects.filter(updated__gte=since, activityId=activityId)
            except ValidationError:
                err_msg = 'Since field is not in correct format for retrieval of activity profile IDs'
                raise ParamError(err_msg) 
            ids = [p.profileId for p in profs]
        else:
            #Return all IDs of profiles associated with this activity b/c there is no since param
            ids = ActivityProfile.objects.filter(activityId=activityId).values_list('profileId', flat=True)
        return ids

    @transaction.commit_on_success
    def delete_profile(self, request_dict):
        #Get profile and delete it
        try:
            self.get_profile(request_dict['params']['profileId'], request_dict['params']['activityId']).delete()
        # we don't want it anyway
        except ActivityProfile.DoesNotExist:
            pass
        except IDNotFoundError:
            pass