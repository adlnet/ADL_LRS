import ast
import datetime
import json
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.timezone import utc
from lrs import models
from lrs.exceptions import IDNotFoundError, ParamError
from lrs.util import etag, get_user_from_auth, uri

class ActivityProfileManager():

    @transaction.commit_on_success
    def post_profile(self, request_dict):
        post_profile = request_dict['profile']
        
        profile_id = request_dict['params']['profileId']

        # get / create  profile
        p, created = models.ActivityProfile.objects.get_or_create(activityId=request_dict['params']['activityId'],  profileId=request_dict['params']['profileId'])
        
        if created:
            p.json_profile = post_profile
            p.content_type = request_dict['headers']['CONTENT_TYPE']
            p.etag = etag.create_tag(post_profile)
            
            #Set updated
            if 'headers' in request_dict and ('updated' in request_dict['headers'] and request_dict['headers']['updated']):
                p.updated = request_dict['headers']['updated']
            else:
                p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
        else:
            orig_prof = ast.literal_eval(p.json_profile)
            post_profile = ast.literal_eval(post_profile)
            # json.dumps changes the format of the string rep of the dict
            merged = '%s' % dict(orig_prof.items() + post_profile.items())
            p.json_profile = merged
            p.etag = etag.create_tag(merged)
            p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)

        p.save()

    @transaction.commit_on_success
	#Save profile to desired activity
    def put_profile(self, request_dict):
        #Parse out profile from request_dict
        profile_id = request_dict['params']['profileId']

        #Get the profile, or if not already created, create one
        p,created = models.ActivityProfile.objects.get_or_create(profileId=profile_id,activityId=request_dict['params']['activityId'])
        
        if request_dict['headers']['CONTENT_TYPE'] != "application/json":
            try:
                profile = ContentFile(request_dict['profile'].read())
            except:
                try:
                    profile = ContentFile(request_dict['profile'])
                except:
                    profile = ContentFile(str(request_dict['profile']))

            if not created:
                #If it already exists delete it
                etag.check_preconditions(request_dict,p, required=True)
                if p.profile:
                    p.profile.delete()
            
            self.save_profile(p, created, profile, request_dict)
        else:
            if not created:
                etag.check_preconditions(request_dict, p, required=True)
            the_profile = request_dict['profile']
            p.json_profile = the_profile
            p.content_type = request_dict['headers']['CONTENT_TYPE']
            p.etag = etag.create_tag(the_profile)
            
            #Set updated
            if 'headers' in request_dict and ('updated' in request_dict['headers'] and request_dict['headers']['updated']):
                p.updated = request_dict['headers']['updated']
            else:
                p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)
            p.save()

    def save_profile(self, p, created, profile, request_dict):
        #Save profile content type based on incoming content type header and create etag
        p.content_type = request_dict['headers']['CONTENT_TYPE']
        p.etag = etag.create_tag(profile.read())
        
        #Set updated
        if 'headers' in request_dict and ('updated' in request_dict['headers'] and request_dict['headers']['updated']):
            p.updated = request_dict['headers']['updated']
        else:
            p.updated = datetime.datetime.utcnow().replace(tzinfo=utc)

        #Go to beginning of file
        profile.seek(0)
        
        #If it didn't exist, save it
        if created:
            p.save()

        #Set filename with the activityID and profileID and save
        fn = "%s_%s" % (p.activityId,request_dict.get('filename', p.id))
        p.profile.save(fn, profile)

    def get_profile(self, profileId, activityId):
        #Retrieve the profile with the given profileId and activity
        try:
            return models.ActivityProfile.objects.get(profileId=profileId, activityId=activityId)
        except models.ActivityProfile.DoesNotExist:
            err_msg = 'There is no profile associated with the id: %s' % profileId
            raise IDNotFoundError(err_msg)

    def get_profile_ids(self, activityId, since=None):
        ids = []

        #If there is a since param return all profileIds since then
        if since:
            try:
                # this expects iso6801 date/time format "2013-02-15T12:00:00+00:00"
                profs = models.ActivityProfile.objects.filter(updated__gte=since, activityId=activityId)
            except ValidationError:
                err_msg = 'Since field is not in correct format for retrieval of activity profile IDs'
                raise ParamError(err_msg) 
            ids = [p.profileId for p in profs]
        else:
            #Return all IDs of profiles associated with this activity b/c there is no since param
            ids = models.ActivityProfile.objects.filter(activityId=activityId).values_list('profileId', flat=True)
        return ids

    def delete_profile(self, request_dict):
        #Get profile and delete it
        try:
            prof = self.get_profile(request_dict['params']['profileId'], request_dict['params']['activityId'])
            prof.delete()
        except models.ActivityProfile.DoesNotExist:
            pass #we don't want it anyway
        except IDNotFoundError:
            pass
