from django.http import HttpResponse
from lrs import objects
from lrs.util import etag
import json

def statements_post(req_dict):
    if req_dict['is_get']:
        return HttpResponse("Success -- statements - method = weird POST/GET - params = %s" % req_dict)
    return HttpResponse("Success -- statements - method = POST - body = %s" % req_dict['body'])

def statements_get(req_dict):
    statementId = req_dict.get('statementId', None)
    if statementId:
        return HttpResponse("Success -- statements - method = GET - statementId = %s" % statementId)
    return HttpResponse("Success - statements - method = GET - params = %s" % req_dict)

def statements_put(req_dict):
    statementId = req_dict['statementId']    
    return HttpResponse("Success -- statements - method = PUT - statementId = %s" % statementId)


def activity_state_put(req_dict):
    # test ETag for concurrency
    actstate = objects.ActivityState(req_dict)
    actstate.put()
    return HttpResponse("", status=204)

def activity_state_get(req_dict):
    # add ETag for concurrency
    actstate = objects.ActivityState(req_dict)
    stateId = req_dict.get('stateId', None)
    if stateId: # state id means we want only 1 item
        resource = actstate.get()
        response = HttpResponse(resource.state.read())
        response['ETag'] = '"%s"' %resource.etag
    else: # no state id means we want an array of state ids
        resource = actstate.get_ids()
        response = HttpResponse(json.dumps([k for k in resource]), content_type="application/json")
    return response

def activity_state_delete(req_dict):
    actstate = objects.ActivityState(req_dict)
    actstate.delete()
    return HttpResponse('', status=204)

def activity_profile_put(req_dict):
    # test ETag for concurrency
    activityId = req_dict['activityId']
    profileId = req_dict['profileId']
    return HttpResponse("Success -- activity_profile - method = PUT - activityId = %s - profileId = %s" % (activityId, profileId))

def activity_profile_get(req_dict):
    # add ETag for concurrency
    activityId = req_dict['activityId']
    profileId = req_dict.get('profileId', None)
    if profileId:
        resource = "Success -- activity_profile - method = GET - activityId = %s - profileId = %s" % (activityId, profileId)
    else:
        since = req_dict.get('since', None)
        if since:
            resource = "Success -- activity_profile - method = GET - activityId = %s - since = %s" % (activityId, since)
        else:
            resource = "Success -- activity_profile - method = GET"
    response = HttpResponse(resource)
    response['ETag'] = etag.create_tag(resource)
    return response

def activity_profile_delete(req_dict):
    activityId = req_dict['activityId']
    profileId = req_dict['profileId']
    return HttpResponse("Success -- activity_profile - method = DELETE - activityId = %s - profileId = %s" % (activityId, profileId))


def activities_get(req_dict):
    activityId = req_dict['activityId']
    return HttpResponse("Success -- activities - method = GET - activityId = %s" % activityId)


def actor_profile_put(req_dict):
    # test ETag for concurrency
    actor = req_dict['actor']
    a = objects.Actor(actor, create=True)
    a.put_profile(req_dict)
    return HttpResponse("", status=204)

def actor_profile_get(req_dict):
    # add ETag for concurrency
    actor = req_dict['actor']
    a = objects.Actor(actor)
    
    profileId = req_dict.get('profileId', None)
    if profileId:
        resource = a.get_profile(profileId)
        response = HttpResponse(resource.profile.read(), content_type=resource.content_type)
        response['ETag'] = '"%s"' % resource.etag
        return response

    since = req_dict.get('since', None)
    resource = a.get_profile_ids(since)
    response = HttpResponse(json.dumps([k for k in resource]), content_type="application/json")
    return response

def actor_profile_delete(req_dict):
    actor = req_dict['actor']
    a = objects.Actor(actor)
    profileId = req_dict['profileId']
    a.delete_profile(profileId)
    return HttpResponse('', status=204)


def actors_get(req_dict):
    actor = req_dict['actor']
    a = objects.Actor(actor)
    return HttpResponse(a.full_actor_json(), mimetype="application/json")


# so far unnecessary
class ProcessError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)
