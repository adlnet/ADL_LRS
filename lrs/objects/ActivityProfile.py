from lrs import models
from lrs.exceptions import IDNotFoundError
from lrs.util import etag
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
import json
import pdb
import logging

logger = logging.getLogger('user_system_actions')

class ActivityProfile():
    def __init__(self, log_dict=None):
        self.log_dict = log_dict

    def log_activity_profile(self, msg, func_name, err=False):
        if self.log_dict:
            self.log_dict['message'] = msg + " in %s.%s" % (__name__, func_name)
            if err:
                logger.error(msg=self.log_dict)
            else:
                logger.info(msg=self.log_dict)

	#Save profile to desired activity
    def put_profile(self, request_dict):
        #Parse out profile from request_dict
        try:
            profile = ContentFile(request_dict['profile'].read())
        except:
            try:
                profile = ContentFile(request_dict['profile'])
            except:
                profile = ContentFile(str(request_dict['profile']))

        #Check if activity exists
        try:
            activity = models.activity.objects.get(activity_id=request_dict['activityId'])
        except models.activity.DoesNotExist:
            err_msg = 'There is no activity associated with the id: %s' % request_dict['activityId']
            self.log_activity_profile(err_msg, self.put_profile.__name__, True)
            raise IDNotFoundError(err_msg)

        #Get the profile, or if not already created, create one
        p,created = models.activity_profile.objects.get_or_create(profileId=request_dict['profileId'],activity=activity)
        
        if created:
            self.log_activity_profile("Created Activity Profile", self.put_profile.__name__)
        else:
            #If it already exists delete it
            etag.check_preconditions(request_dict,p, required=True)
            p.profile.delete()
            self.log_activity_profile("Retrieved Activity Profile", self.put_profile.__name__)
        
        #Save profile content type based on incoming content type header and create etag
        p.content_type = request_dict['CONTENT_TYPE']
        p.etag = etag.create_tag(profile.read())
        
        #Set updated
        if request_dict['updated']:
            p.updated = request_dict['updated']
        
        #Go to beginning of file
        profile.seek(0)
        
        #If it didn't exist, save it
        if created:
            p.save()

        #Set filename with the activityID and profileID and save
        fn = "%s_%s" % (p.activity_id,request_dict.get('filename', p.id))
        p.profile.save(fn, profile)

        self.log_activity_profile("Saved Activity Profile", self.put_profile.__name__)


    def get_profile(self, profileId, activityId):
        #Make sure activityId exists
        try:
            activity = models.activity.objects.get(activity_id=activityId)
        except models.activity.DoesNotExist:
            err_msg = 'There is no activity associated with the id: %s' % activityId
            self.log_activity_profile(err_msg, self.get_profile.__name__, True)
            raise IDNotFoundError(err_msg)

        #Retrieve the profile with the given profileId and activity
        try:
            return models.activity_profile.objects.get(profileId=profileId, activity=activity)
        except models.activity_profile.DoesNotExist:
            err_msg = 'There is no profile associated with the id: %s' % profileId
            self.log_activity_profile(err_msg, self.get_profile.__name__, True)
            raise IDNotFoundError(err_msg)


    def get_profile_ids(self, profileId, activityId, since=None):
        ids = []

        #make sure activityId exists
        try:
            activity = models.activity.objects.get(activity_id=activityId)
        except models.activity.DoesNotExist:
            err_msg = 'There is no activity associated with the id: %s' % activityId
            self.log_activity_profile(err_msg, self.get_profile_ids.__name__, True)
            raise IDNotFoundError(err_msg)

        #If there is a since param return all profileIds since then
        if since:
            try:
                profs = models.activity_profile.objects.filter(updated__gte=since, profileId=profileId, activity=activity)
            except ValidationError:
                since_i = int(float(since))
                since_dt = datetime.datetime.fromtimestamp(since_i)
                profs = models.activity_profile_set.filter(update__gte=since_dt, profileId=profileId, activity=activity)
            ids = [p.profileId for p in profs]
        else:
            #Return all IDs of profiles associated with this activity b/c there is no since param
            ids = models.activity_profile.objects.filter(activity=activity).values_list('profileId', flat=True)
        return ids

    def delete_profile(self, request_dict):
        #Get profile and delete it
        try:
            prof = self.get_profile(request_dict['profileId'], request_dict['activityId'])
            prof.delete()
        except models.activity_profile.DoesNotExist:
            pass #we don't want it anyway
        except IDNotFoundError:
            pass
