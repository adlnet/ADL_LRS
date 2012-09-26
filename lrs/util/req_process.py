from django.http import HttpResponse
from lrs import objects, models
from lrs.util import etag
import json
from lrs.objects import Actor, Activity, ActivityState, ActivityProfile, Statement
import uuid
import pdb
import retrieve_statement

import pprint

def statements_post(req_dict):
    #TODO: more elegant way of doing this?
    if req_dict['method'] == 'GET': #type(req_dict) is dict:
        stmtList = retrieve_statement.complexGet(req_dict['body'])
        # pdb.set_trace()
        statementResult = retrieve_statement.buildStatementResult(req_dict.copy(),stmtList)
        return HttpResponse(json.dumps(statementResult, indent=4), mimetype="application/json", status=200)
    else:
        stmtResponses = []
        if not type(req_dict['body']) is list:
            stmt = Statement.Statement(req_dict['body'], auth=req_dict['user']).statement
            stmtResponses.append(str(stmt.statement_id))
        else:
            for st in req_dict['body']:
                stmt = Statement.Statement(st, auth=req_dict['user']).statement
                stmtResponses.append(str(stmt.statement_id))
        # return HttpResponse("StatementID(s) = %s" % stmtResponses, status=200)
        return HttpResponse(stmtResponses, status=200)

def statements_put(req_dict):
    statementId = req_dict['body']['statementId']
    try:
        stmt = models.statement.objects.get(statement_id=statementId)
    except models.statement.DoesNotExist:
        stmt = Statement.Statement(req_dict['body'], auth=req_dict['user']).statement        
        return HttpResponse("StatementID = %s" % statementId, status=200)
    else:
        return HttpResponse("Error: %s already exists" % statementId, status=204)
     
def statements_get(req_dict):
    # pdb.set_trace()
    statementResult = {}
    try:
        statementId = req_dict['statementId']
        st = Statement.Statement(statement_id=statementId, get=True)
        # data = json.dumps(st.get_full_statement_json(), indent=4, sort_keys=True)
        statementResult['statements'] = json.dumps(st.get_full_statement_json())
        # return HttpResponse(data, mimetype="application/json")
    except:
        stmtList = retrieve_statement.complexGet(req_dict)
        statementResult = retrieve_statement.buildStatementResult(req_dict.copy(), stmtList)
    
    return HttpResponse(json.dumps(statementResult, indent=4), mimetype="application/json", status=200)

def activity_state_put(req_dict):
    # test ETag for concurrency
    actstate = ActivityState.ActivityState(req_dict)
    actstate.put()
    return HttpResponse("", status=204)

def activity_state_get(req_dict):
    # add ETag for concurrency
    actstate = ActivityState.ActivityState(req_dict)
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
    actstate = ActivityState.ActivityState(req_dict)
    actstate.delete()
    return HttpResponse('', status=204)

def activity_profile_put(req_dict):
    #Instantiate ActivityProfile
    ap = ActivityProfile.ActivityProfile()

    #Put profile and return 204 response
    ap.put_profile(req_dict)
    return HttpResponse('Success -- activity profile - method = PUT - profileId = %s' % req_dict['profileId'], status=200)

def activity_profile_get(req_dict):
    #TODO:need eTag for returning list of IDs?

    #Instantiate ActivityProfile
    ap = ActivityProfile.ActivityProfile()
    
    #Get profileId and activityId
    profileId = req_dict.get('profileId', None)
    activityId = req_dict.get('activityId', None)

    #If the profileId exists, get the profile and return it in the response
    if profileId:
        resource = ap.get_profile(profileId, activityId)
        response = HttpResponse(resource.profile.read(), content_type=resource.content_type)
        response['ETag'] = '"%s"' % resource.etag
        return response

    #Return IDs of profiles stored since profileId was not submitted
    since = req_dict.get('since', None)
    resource = ap.get_profile_ids(since, activityId)
    response = HttpResponse(json.dumps([k for k in resource]), content_type="application/json")
    response['since'] = since
    #response['ETag'] = '"%s"' % resource.etag
    return response


def activity_profile_delete(req_dict):
    #Instantiate activity profile
    ap = ActivityProfile.ActivityProfile()

    #Delete profile and return success
    ap.delete_profile(req_dict)
    return HttpResponse('Success -- activity profile - method = DELETE - profileId = %s' % req_dict['profileId'], status=200)

def activities_get(req_dict):
    activityId = req_dict['activityId']
    a = Activity.Activity(activity_id=activityId, get=True)
    data = a.get_full_activity_json()
    return HttpResponse(stream_response_generator(data), mimetype="application/json")
    
#Generate JSON
def stream_response_generator(data): 
    first = True
    yield '{'
    for k,v in data.items():
        if not first:
            yield ', '
        else:
            first = False
        #Catch next dictionaries
        if type(v) is dict:
            stream_response_generator(v)
        #Catch lists as dictionary values
        if type(v) is list:
            lfirst = True
            yield json.dumps(k)
            yield ': '
            yield '['
            for item in v:
                if not lfirst:
                    yield ', '
                else:
                    lfirst = False  
                #Catch dictionaries as items in a list    
                if type(item) is dict:
                    stream_response_generator(item)
                yield json.dumps(item)
            yield ']'
        else:
            yield json.dumps(k)
            yield ': '
            yield json.dumps(v)
    yield '}'

def actor_profile_put(req_dict):
    # test ETag for concurrency
    actor = req_dict['actor']
    a = Actor.Actor(actor, create=True)
    a.put_profile(req_dict)
    return HttpResponse("", status=204)

def actor_profile_get(req_dict):
    # add ETag for concurrency
    actor = req_dict['actor']
    a = Actor.Actor(actor)
    
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
    a = Actor.Actor(actor)
    profileId = req_dict['profileId']
    a.delete_profile(profileId)
    return HttpResponse('', status=204)


def actors_get(req_dict):
    actor = req_dict['actor']
    a = Actor.Actor(actor)
    return HttpResponse(a.full_actor_json(), mimetype="application/json")


# so far unnecessary
class ProcessError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)
