import datetime
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from lrs import models
from lrs.exceptions import IDNotFoundError
from lrs.util import etag, get_user_from_auth, log_message, update_parent_log_status
import logging
import pdb

logger = logging.getLogger('user_system_actions')

class ActivityProfile():
    def __init__(self, log_dict=None):
        self.log_dict = log_dict

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
            # Always want global version
            activity = models.activity.objects.get(activity_id=request_dict['activityId'],
                global_representation=True)
        except models.activity.DoesNotExist:
            err_msg = 'There is no activity associated with the id: %s' % request_dict['activityId']
            log_message(self.log_dict, err_msg, __name__, self.put_profile.__name__, True)
            update_parent_log_status(self.log_dict, 404)
            raise IDNotFoundError(err_msg)

        user = get_user_from_auth(request_dict.get('auth', None))
        #Get the profile, or if not already created, create one
        p,created = models.activity_profile.objects.get_or_create(profileId=request_dict['profileId'],activity=activity, user=user)
        
        if created:
            log_message(self.log_dict, "Created Activity Profile", __name__, self.put_profile.__name__)
        else:
            #If it already exists delete it
            etag.check_preconditions(request_dict,p, required=True)
            p.profile.delete()
            log_message(self.log_dict, "Retrieved Activity Profile", __name__, self.put_profile.__name__)
        
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

        log_message(self.log_dict, "Saved Activity Profile", __name__, self.put_profile.__name__)


    def get_profile(self, profileId, activityId):
        #Make sure activityId exists
        log_message(self.log_dict, "Getting profile with profile id: %s -- activity id: %s" % (profileId, activityId),
            __name__, self.get_profile.__name__)
        try:
            # Always want global version
            activity = models.activity.objects.get(activity_id=activityId, global_representation=True)
        except models.activity.DoesNotExist:
            err_msg = 'There is no activity associated with the id: %s' % activityId
            log_message(self.log_dict, err_msg, __name__, self.get_profile.__name__, True)
            update_parent_log_status(self.log_dict, 404)
            raise IDNotFoundError(err_msg)

        #Retrieve the profile with the given profileId and activity
        try:
            return models.activity_profile.objects.get(profileId=profileId, activity=activity)
        except models.activity_profile.DoesNotExist:
            err_msg = 'There is no profile associated with the id: %s' % profileId
            log_message(self.log_dict, err_msg, __name__, self.get_profile.__name__, True)
            update_parent_log_status(self.log_dict, 404)
            raise IDNotFoundError(err_msg)


    def get_profile_ids(self, activityId, since=None):
        ids = []

        #make sure activityId exists
        try:
            # Always want global version
            activity = models.activity.objects.get(activity_id=activityId, global_representation=True)
        except models.activity.DoesNotExist:
            err_msg = 'There is no activity associated with the id: %s' % activityId
            log_message(self.log_dict, err_msg, __name__, self.get_profile_ids.__name__, True)
            update_parent_log_status(self.log_dict, 404)
            raise IDNotFoundError(err_msg)

        #If there is a since param return all profileIds since then
        if since:
            try:
                # this expects iso6801 date/time format "2013-02-15T12:00:00+00:00"
                profs = models.activity_profile.objects.filter(updated__gte=since, activity=activity)
            except ValidationError:
                from django.utils import timezone
                since_i = int(float(since))# this handles timestamp like str(time.time())
                since_dt = datetime.datetime.fromtimestamp(since_i).replace(tzinfo=timezone.get_default_timezone())
                profs = models.activity_profile.objects.filter(updated__gte=since_dt, activity=activity)
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
