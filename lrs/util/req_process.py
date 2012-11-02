from django.http import HttpResponse
from lrs import objects, models
from lrs.util import etag
import json
from lrs.objects import Agent, Activity, ActivityState, ActivityProfile, Statement
from django.db import transaction
import uuid
import pdb
import ast
import retrieve_statement

import pprint

def statements_post(req_dict):
    stmtResponses = []
    if isinstance(req_dict['body'], str):
        try:
            req_dict['body'] = ast.literal_eval(req_dict['body'])
        except:
            req_dict['body'] = json.loads(req_dict['body'])    
        if not type(req_dict['body']) is list:
            stmt = Statement.Statement(req_dict['body'], auth=req_dict['user']).statement
            stmtResponses.append(str(stmt.statement_id))
        else:
            try:
                for st in req_dict['body']:
                    stmt = Statement.Statement(st, auth=req_dict['user']).statement
                    stmtResponses.append(str(stmt.statement_id))
            except Exception, e:
                for stmt_id in stmtResponses:
                    try:
                        # pdb.set_trace()
                        models.statement.objects.get(statement_id=stmt_id).delete()
                    except models.statement.DoesNotExist:
                        pass # stmt already deleted
                raise e

    return HttpResponse(stmtResponses, status=200)

def statements_put(req_dict):
    req_dict['body']['statement_id'] = req_dict['statementId']
    stmt = Statement.Statement(req_dict['body'], auth=req_dict['user']).statement
    return HttpResponse("No Content", status=204)
     
def statements_get(req_dict):
    # If statementId is in req_dict then it is a single get
    if 'statementId' in req_dict:
        statementId = req_dict['statementId']
        # Try to retrieve stmt, if DNE then return empty else return stmt info
        try:
            st = Statement.Statement(statement_id=statementId, get=True, auth=req_dict['user'])
        except Exception, e:
            raise e
        stmt_data = st.get_full_statement_json()
        return HttpResponse(json.dumps(stmt_data), mimetype="application/json", status=200)    
    # If statementId is not in req_dict then it is a complex GET
    else:
        statementResult = {}
        stmtList = retrieve_statement.complexGet(req_dict)
        statementResult = retrieve_statement.buildStatementResult(req_dict.copy(), stmtList)
    return HttpResponse(json.dumps(statementResult), mimetype="application/json", status=200)

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
        resource = actstate.get(req_dict['user'])
        response = HttpResponse(resource.state.read())
        response['ETag'] = '"%s"' %resource.etag
    else: # no state id means we want an array of state ids
        resource = actstate.get_ids(req_dict['user'])
        response = HttpResponse(json.dumps([k for k in resource]), content_type="application/json")
    return response

def activity_state_delete(req_dict):
    actstate = ActivityState.ActivityState(req_dict)
    actstate.delete(req_dict['user'])
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
    # Try to retrieve activity, if DNE then return empty else return activity info
    act_list = models.activity.objects.filter(activity_id=activityId)
    if len(act_list) == 0:
        raise IDNotFoundError("No activities found with ID %s" % activityId)
    full_act_list = []
    for act in act_list:
        full_act_list.append(act.object_return())
    # return HttpResponse(stream_response_generator(data), mimetype="application/json")
    return HttpResponse(full_act_list, mimetype="application/json", status=200)

    
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

def agent_profile_put(req_dict):
    # test ETag for concurrency
    agent = req_dict['agent']
    a = Agent.Agent(agent, create=True)
    a.put_profile(req_dict)
    return HttpResponse("", status=204)

def agent_profile_get(req_dict):
    # add ETag for concurrency
    agent = req_dict['agent']
    a = Agent.Agent(agent)
    
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

def agent_profile_delete(req_dict):
    agent = req_dict['agent']
    a = Agent.Agent(agent)
    profileId = req_dict['profileId']
    a.delete_profile(profileId)
    return HttpResponse('', status=204)

def agents_get(req_dict):
    agent = req_dict['agent']
    a = Agent.Agent(agent)
    return HttpResponse(a.get_person_json(), mimetype="application/json")


# so far unnecessary
class IDNotFoundError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)