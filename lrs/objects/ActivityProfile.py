from lrs import models
from lrs.util import etag
from django.core.files.base import ContentFile
from Activity import IDNotFoundError

class ActivityProfile():

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
            raise IDNotFoundError('There is no activity associated with the id: %s' % request_dict['activityId'])

        #Get the profile, or if not already created, create one
        p,created = models.activity_profile.objects.get_or_create(profileId=request_dict['profileId'],activity=activity)
        
        #If it already exists delete it
        if not created:
            etag.check_preconditions(request_dict,p, required=True)
            p.profile.delete()
        
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


    def get_profile(self, profileId, activityId):
        #Make sure activityId exists
        try:
            activity = models.activity.objects.get(activity_id=activityId)
        except models.activity.DoesNotExist:
            raise IDNotFoundError('There is no activity associated with the id: %s' % activityId)

        #Retrieve the profile with the given profileId and activity
        try:
            return models.activity_profile.objects.get(profileId=profileId, activity=activity)
        except models.activity_profile.DoesNotExist:
            raise IDNotFoundError('There is no profile associated with the id: %s' % profileId)


    def get_profile_ids(self, profileId, activityId, since=None):
        ids = []

        #make sure activityId exists
        try:
            activity = models.activity.objects.get(activity_id=activityId)
        except models.activity.DoesNotExist:
            raise IDNotFoundError('There is no activity associated with the id: %s' % activityId)

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

class ForbiddenException(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)