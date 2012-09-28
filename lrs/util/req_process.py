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
    statement_result = {}
    # If just POSTing a sinlge stmt (req_dict data will not be in list)
    if not type(req_dict[0]['body']) is list:
        stmt = Statement.Statement(req_dict[0]['body'], auth=req_dict[1]).statement
        statement_result['statement ID(s)'] = str(stmt.statement_id)
    # POSTing multiple stmts
    else:
        stmt_responses = []
        for st in req_dict[0]['body']:
            stmt = Statement.Statement(st, auth=req_dict[1]).statement
            stmt_responses.append(str(stmt.statement_id))
        statement_result['statement ID(s)'] = stmtResponses
    return HttpResponse(json.dumps(statement_result, indent=4), status=200)    

def statements_put(req_dict):
    statement_result = {}
    # Retrieve ID
    statement_id = req_dict[0]['statementId']

    # Already checked if it exists and it doesn't so add ID to the dict and create stmt
    req_dict[0]['body']['statement_id'] = statement_id 
    stmt = Statement.Statement(req_dict[0]['body'], auth=req_dict[1]).statement        
    statement_result['statement ID(s)'] = str(stmt.statement.statement_id)
    return HttpResponse(json.dumps(statement_result, indent=4), mimetype="application/json", status=200)
     
def statements_get(req_dict):
    # If statementId is in req_dict then it is a single get
    if 'statementId' in req_dict:
        statementId = req_dict['statementId']
        
        # Try to retrieve stmt, if DNE then return empty else return stmt info
        try:
            st = Statement.Statement(statement_id=statementId, get=True)
        except Exception, e:
            return HttpResponse(json.dumps([]), mimetype="application/json", status=200)
        
        stmt_data = st.get_full_statement_json()
        return HttpResponse(json.dumps(stmt_data, indent=4), mimetype="application/json", status=200)
    
    # If statementId is not in req_dict then it is a complex GET
    else:
        statement_result = {}
        stmt_list = retrieve_statement.complexGet(req_dict)
        statement_result = retrieve_statement.buildStatementResult(req_dict.copy(), stmt_list)
    
    return HttpResponse(json.dumps(statement_result, indent=4), mimetype="application/json", status=200)

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
