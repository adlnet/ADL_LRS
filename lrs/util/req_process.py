import json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from django.http import HttpResponse
from lrs import models, exceptions
from lrs.util import log_info_processing, log_exception, update_parent_log_status
from lrs.objects import Agent, Activity, ActivityState, ActivityProfile, Statement
import retrieve_statement
import pprint
import pdb

def statements_post(req_dict):
    stmt_responses = []
    log_dict = req_dict['initial_user_action'] 
    log_info_processing(log_dict, 'POST', __name__)

    define = True
    if 'oauth_define' in req_dict:
        define = req_dict['oauth_define']    

    # Handle batch POST
    if type(req_dict['body']) is list:
        try:
            for st in req_dict['body']:
                stmt = Statement.Statement(st, auth=req_dict['auth'], log_dict=log_dict,
                    define=define).model_object
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
        stmt = Statement.Statement(req_dict['body'], auth=req_dict['auth'], log_dict=log_dict,
            define=define).model_object
        stmt_responses.append(stmt.statement_id)

    update_parent_log_status(log_dict, 200)

    return HttpResponse(json.dumps([st for st in stmt_responses]), mimetype="application/json", status=200)

def statements_put(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'PUT', __name__)

    define = True
    if 'oauth_define' in req_dict:
        define = req_dict['oauth_define']    

    # Set statement ID in body so all data is together
    req_dict['body']['statement_id'] = req_dict['statementId']
    stmt = Statement.Statement(req_dict['body'], auth=req_dict['auth'], log_dict=log_dict,
        define=define).model_object
    
    update_parent_log_status(log_dict, 204)
    return HttpResponse("No Content", status=204)

def statements_more_get(req_dict):
    stmt_result, attachments = retrieve_statement.get_statement_request(req_dict['more_id'])     
    content_length = len(json.dumps(stmt_result))
    mime_type = "application/json"

    # If there are attachments, include them in the payload
    if attachments:
        stmt_result, mime_type, content_length = build_response(req_dict, stmt_result, content_length)
        resp = HttpResponse(stmt_result, mimetype=mime_type, status=200)
    # If not, just dump the stmt_result
    else:
        resp = HttpResponse(json.dumps(stmt_result), mimetype=mime_type, status=200)
    
    # Add consistent header and set content-length
    try:
        resp['X-Experience-API-Consistent-Through'] = str(models.statement.objects.latest('stored').stored)
    except:
        resp['X-Experience-API-Consistent-Through'] = str(datetime.now())
    resp['Content-Length'] = str(content_length)
    return resp

def statements_get(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'GET', __name__)
    
    if 'statements_mine_only' in req_dict:
        mine_only = True
    else:
        mine_only = False

    stmt_result = {}
    mime_type = "application/json"
    # If statementId is in req_dict then it is a single get
    if 'statementId' in req_dict or 'voidedStatementId' in req_dict:
        if 'statementId' in req_dict:
            statementId = req_dict['statementId']
            voided = False
        else:
            statementId = req_dict['voidedStatementId']
            voided = True

        # Try to retrieve stmt, if DNE then return empty else return stmt info                
        try:
            st = models.statement.objects.get(statement_id=statementId)
        except models.statement.DoesNotExist:
            err_msg = 'There is no statement associated with the id: %s' % statementId
            log_exception(log_dict, err_msg, statements_get.__name__)
            update_parent_log_status(log_dict, 404)
            raise exceptions.IDNotFoundError(err_msg)

        if mine_only and st.authority.id != req_dict['auth'].id:
            err_msg = "Incorrect permissions to view statements that do not have auth %s" % str(req_dict['auth'])
            log_exception(log_dict, err_msg, statements_get.__name__)
            update_parent_log_status(log_dict, 403)
            raise exceptions.Forbidden(err_msg)
        
        if st.voided != voided:
            if st.voided:
                err_msg = 'The requested statement (%s) is voided. Use the "voidedStatementId" parameter to retrieve your statement.' % statementId
            else:
                err_msg = 'The requested statement (%s) is not voided. Use the "statementId" parameter to retrieve your statement.' % statementId
            log_exception(log_dict, err_msg, statements_get.__name__)
            update_parent_log_status(log_dict, 404)
            raise exceptions.IDNotFoundError(err_msg)
        
        # Once validated, return the object, dump to json, and set content length
        stmt_result = json.dumps(st.object_return())
        resp = HttpResponse(stmt_result, mimetype=mime_type, status=200)
        content_length = len(json.dumps(stmt_result))
    # Complex GET
    else:
        # Create returned stmt list from the req dict
        stmt_list = retrieve_statement.complex_get(req_dict)
        # Build json result({statements:...,more:...}) and set content length
        stmt_result = retrieve_statement.build_statement_result(req_dict, stmt_list)
        content_length = len(json.dumps(stmt_result))

        # If attachments=True in req_dict then include the attachment payload and return different mime type
        if 'attachments' in req_dict and req_dict['attachments']:
            stmt_result, mime_type, content_length = build_response(req_dict, stmt_result, content_length)
            resp = HttpResponse(stmt_result, mimetype=mime_type, status=200)
        # Else attachments are false for the complex get so just dump the stmt_result
        else:
            resp = HttpResponse(json.dumps(stmt_result), mimetype=mime_type, status=200)
    
    # Set consistent through and content length headers for all responses
    try:
        resp['X-Experience-API-Consistent-Through'] = str(models.statement.objects.latest('stored').stored)
    except:
        resp['X-Experience-API-Consistent-Through'] = str(datetime.now())
    
    resp['Content-Length'] = str(content_length)
    update_parent_log_status(log_dict, 200)    
    return resp

def build_response(req_dict, stmt_result, content_length):
    sha2s = []
    mime_type = "application/json"
    statements = stmt_result['statements']
    # Iterate through each attachment in each statement
    for stmt in statements:
        if 'attachments' in stmt:
            for attachment in stmt['attachments']:
                if 'sha2' in attachment:
                    # If there is a sha2-retrieve the StatementAttachment object and add the payload to sha2s
                    att_object = models.StatementAttachment.objects.get(sha2=attachment['sha2'])
                    sha2s.append((attachment['sha2'], att_object.payload))    
    
    # If attachments have payloads
    if sha2s:
        # Create multipart message and attach json message to it
        full_message = MIMEMultipart(boundary="ADL_LRS---------")
        stmt_message = MIMEApplication(json.dumps(stmt_result), _subtype="json", _encoder=json.JSONEncoder)
        full_message.attach(stmt_message)
        # For each sha create a binary message, and attach to the multipart message
        for sha2 in sha2s:
            binary_message = MIMEBase('application', 'octet-stream')
            binary_message.set_payload(sha2[1].read())
            binary_message.add_header('X-Experience-API-Hash', sha2[0])
            binary_message.add_header('Content-Transfer-Encoding', 'binary')
            full_message.attach(binary_message)
            # Increment size on content-length and set mime type
            content_length += sha2[1].size
            mime_type = "multipart/mixed"
            return full_message.as_string(), mime_type, content_length 
    # Has attachments but no payloads so just dump the stmt_result
    else:
        return json.dumps(stmt_result), mime_type, content_length

def activity_state_post(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'POST', __name__)

    # test ETag for concurrency
    actstate = ActivityState.ActivityState(req_dict, log_dict=log_dict)
    actstate.post()

    update_parent_log_status(log_dict, 204)
    return HttpResponse("", status=204)

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
    log_info_processing(log_dict, req_dict['method'], __name__)

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

def activity_profile_post(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'POST', __name__)

    #Instantiate ActivityProfile
    ap = ActivityProfile.ActivityProfile(log_dict=log_dict)
    #Put profile and return 204 response
    ap.post_profile(req_dict)

    update_parent_log_status(log_dict, 204)
    return HttpResponse('', status=204)

def activity_profile_put(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'PUT', __name__)

    #Instantiate ActivityProfile
    ap = ActivityProfile.ActivityProfile(log_dict=log_dict)
    #Put profile and return 204 response
    ap.put_profile(req_dict)

    update_parent_log_status(log_dict, 204)
    return HttpResponse('', status=204)

def activity_profile_get(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, req_dict['method'], __name__)

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
    resource = ap.get_profile_ids(activityId,since)
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

    update_parent_log_status(log_dict, 204)
    return HttpResponse('', status=204)

def activities_get(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, req_dict['method'], __name__)

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

    resp = HttpResponse(json.dumps([k for k in full_act_list]), mimetype="application/json", status=200)
    resp['Content-Length'] = str(len(json.dumps(full_act_list)))
    update_parent_log_status(log_dict, 200)
    return resp

def agent_profile_post(req_dict):
    log_dict = req_dict['initial_user_action']    
    log_info_processing(log_dict, 'POST', __name__)

    # test ETag for concurrency
    agent = req_dict['agent']
    a = Agent.Agent(agent, create=True, log_dict=log_dict)
    a.post_profile(req_dict)

    update_parent_log_status(log_dict, 204)
    return HttpResponse("", status=204)

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
    log_info_processing(log_dict, req_dict['method'], __name__)

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
    log_info_processing(log_dict, req_dict['method'], __name__)

    agent = req_dict['agent']
    a = Agent.Agent(agent,log_dict=log_dict)
    agent_data = a.get_person_json()
    resp = HttpResponse(agent_data, mimetype="application/json")
    resp['Content-Length'] = str(len(agent_data))
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
