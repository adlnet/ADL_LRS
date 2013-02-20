from django.http import HttpResponse
from lrs import objects, models, exceptions
from lrs.util import etag
from lrs.util import log_info_processing, log_exception, update_parent_log_status
import json
from lrs.objects import Agent, Activity, ActivityState, ActivityProfile, Statement
import json
import retrieve_statement
import pprint

import pdb

def statements_post(req_dict):
    stmt_responses = []

    log_dict = req_dict['initial_user_action'] 
    log_info_processing(log_dict, 'POST', __name__)

    # Handle batch POST
    if type(req_dict['body']) is list:
        try:
            for st in req_dict['body']:
                stmt = Statement.Statement(st, auth=req_dict['auth'], log_dict=log_dict).model_object
                stmt_responses.append(str(stmt.statement_id))
        except Exception, e:
            for stmt_id in stmt_responses:
                try:
                    models.statement.objects.get(statement_id=stmt_id).delete()
                except models.statement.DoesNotExist:
                    pass # stmt already deleted 
            log_exception(log_dict, e.message, statements_post.__name__)
            update_parent_log_status(log_dict, 500)
            raise e
    else:
        # Handle single POST
        stmt = Statement.Statement(req_dict['body'], auth=req_dict['auth'], log_dict=log_dict).model_object
        stmt_responses.append(str(stmt.statement_id))

    update_parent_log_status(log_dict, 200)

    return HttpResponse(stmt_responses, status=200)

def statements_put(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'PUT', __name__)

    # Set statement ID in body so all data is together
    req_dict['body']['statement_id'] = req_dict['statementId']
    stmt = Statement.Statement(req_dict['body'], auth=req_dict['auth'], log_dict=log_dict).model_object
    
    update_parent_log_status(log_dict, 204)
    return HttpResponse("No Content", status=204)
     
def statements_get(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'GET', __name__)

    stmt_result = {}
    # If statementId is in req_dict then it is a single get
    if 'statementId' in req_dict:
        statementId = req_dict['statementId']
        # Try to retrieve stmt, if DNE then return empty else return stmt info                
        try:
            st = models.statement.objects.get(statement_id=statementId)
        except models.statement.DoesNotExist:
            err_msg = 'There is no statement associated with the id: %s' % statementId
            log_exception(log_dict, err_msg, statements_get.__name__)
            update_parent_log_status(log_dict, 404)
            raise exceptions.IDNotFoundError(err_msg)
        stmt_result = st.object_return()
    else:
        stmt_list = retrieve_statement.complex_get(req_dict)
        stmt_result = retrieve_statement.build_statement_result(req_dict.copy(), stmt_list)
    
    update_parent_log_status(log_dict, 200)
    return HttpResponse(stream_response_generator(stmt_result), mimetype="application/json", status=200)

def activity_state_put(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'PUT', __name__)

    # test ETag for concurrency
    actstate = ActivityState.ActivityState(req_dict, log_dict=log_dict)
    actstate.put()

    update_parent_log_status(log_dict, 204)
    return HttpResponse("", status=204)

def activity_state_get(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'GET', __name__)

    # add ETag for concurrency
    actstate = ActivityState.ActivityState(req_dict, log_dict=log_dict)
    stateId = req_dict.get('stateId', None)
    if stateId: # state id means we want only 1 item
        resource = actstate.get(req_dict['auth'])
        response = HttpResponse(resource.state.read())
        response['ETag'] = '"%s"' %resource.etag
    else: # no state id means we want an array of state ids
        resource = actstate.get_ids(req_dict['auth'])
        response = HttpResponse(json.dumps([k for k in resource]), content_type="application/json")
    update_parent_log_status(log_dict, 200)
    return response

def activity_state_delete(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'DELETE', __name__)

    actstate = ActivityState.ActivityState(req_dict, log_dict=log_dict)
    # Delete state
    actstate.delete(req_dict['auth'])

    update_parent_log_status(log_dict, 204)
    return HttpResponse('', status=204)

def activity_profile_put(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'PUT', __name__)

    #Instantiate ActivityProfile
    ap = ActivityProfile.ActivityProfile(log_dict=log_dict)
    #Put profile and return 204 response
    ap.put_profile(req_dict)

    update_parent_log_status(log_dict, 200)
    return HttpResponse('Success -- activity profile - method = PUT - profileId = %s' % req_dict['profileId'], status=200)

def activity_profile_get(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'GET', __name__)

    #TODO:need eTag for returning list of IDs?
    # Instantiate ActivityProfile
    ap = ActivityProfile.ActivityProfile(log_dict=log_dict)
    # Get profileId and activityId
    profileId = req_dict.get('profileId', None)
    activityId = req_dict.get('activityId', None)

    #If the profileId exists, get the profile and return it in the response
    if profileId:
        resource = ap.get_profile(profileId, activityId)
        response = HttpResponse(resource.profile.read(), content_type=resource.content_type)
        response['ETag'] = '"%s"' % resource.etag
        update_parent_log_status(log_dict, 200)
        return response

    #Return IDs of profiles stored since profileId was not submitted
    since = req_dict.get('since', None)
    resource = ap.get_profile_ids(since, activityId)
    response = HttpResponse(json.dumps([k for k in resource]), content_type="application/json")
    response['since'] = since
    #response['ETag'] = '"%s"' % resource.etag
    update_parent_log_status(log_dict, 200)
    return response


def activity_profile_delete(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'DELETE', __name__)

    #Instantiate activity profile
    ap = ActivityProfile.ActivityProfile(log_dict=log_dict)
    # Delete profile and return success
    ap.delete_profile(req_dict)

    update_parent_log_status(log_dict, 200)
    return HttpResponse('Success -- activity profile - method = DELETE - profileId = %s' % req_dict['profileId'], status=200)

def activities_get(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'GET', __name__)

    activityId = req_dict['activityId']
    # Try to retrieve activity, if DNE then return empty else return activity info
    act_list = models.activity.objects.filter(activity_id=activityId)
    if not act_list:
        err_msg = "No activities found with ID %s" % activityId
        log_exception(log_dict, err_msg, activities_get.__name__)
        update_parent_log_status(log_dict, 404)
        raise exceptions.IDNotFoundError(err_msg)
    
    full_act_list = []
    for act in act_list:
        full_act_list.append(act.object_return())

    update_parent_log_status(log_dict, 200)
    return HttpResponse(json.dumps([k for k in full_act_list]), mimetype="application/json", status=200)

def agent_profile_put(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'PUT', __name__)

    # test ETag for concurrency
    agent = req_dict['agent']
    a = Agent.Agent(agent, create=True, log_dict=log_dict)
    a.put_profile(req_dict)

    update_parent_log_status(log_dict, 204)
    return HttpResponse("", status=204)

def agent_profile_get(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'GET', __name__)

    # add ETag for concurrency
    agent = req_dict['agent']
    a = Agent.Agent(agent, log_dict=log_dict)
    
    profileId = req_dict.get('profileId', None)
    if profileId:
        resource = a.get_profile(profileId)
        response = HttpResponse(resource.profile.read(), content_type=resource.content_type)
        response['ETag'] = '"%s"' % resource.etag
        update_parent_log_status(log_dict, 200)
        return response

    since = req_dict.get('since', None)
    resource = a.get_profile_ids(since)
    response = HttpResponse(json.dumps([k for k in resource]), content_type="application/json")
    update_parent_log_status(log_dict, 200)
    return response

def agent_profile_delete(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'DELETE', __name__)

    agent = req_dict['agent']
    a = Agent.Agent(agent, log_dict=log_dict)
    profileId = req_dict['profileId']
    a.delete_profile(profileId)

    update_parent_log_status(log_dict, 204)
    return HttpResponse('', status=204)

def agents_get(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'GET', __name__)

    agent = req_dict['agent']
    a = Agent.Agent(agent,log_dict=log_dict)
    resp = HttpResponse(a.get_person_json(), mimetype="application/json")
    update_parent_log_status(log_dict, 200)
    return resp

#Generate JSON
def stream_response_generator(data):
    first = True
    yield "{"
    for k,v in data.items():
        if not first:
            yield ", "
        else:
            first = False
        #Catch nested dictionaries
        if type(v) is dict:
            stream_response_generator(v)
        #Catch lists as dictionary values
        if type(v) is list:
            lfirst = True
            yield json.dumps(k)
            yield ": "
            yield "["
            for item in v:
                if not lfirst:
                    yield ", "
                else:
                    lfirst = False
                #Catch dictionaries as items in a list
                if type(item) is dict:
                    stream_response_generator(item)
                yield json.dumps(item)
            yield "]"
        else:
            yield json.dumps(k)
            yield ": "
            yield json.dumps(v)
    yield "}"
