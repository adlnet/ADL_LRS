import json
import uuid
import copy
from base64 import b64decode

from datetime import datetime

from django.http import HttpResponse, HttpResponseNotFound
from django.conf import settings
from django.db import transaction
from django.utils.timezone import utc
from util import convert_to_dict
from retrieve_statement import complex_get, get_more_statement_request
from ..models import Statement, StatementAttachment, Agent, Activity
from ..managers.ActivityProfileManager import ActivityProfileManager
from ..managers.ActivityStateManager import ActivityStateManager 
from ..managers.AgentProfileManager import AgentProfileManager
from ..managers.StatementManager import StatementManager

def process_statement(stmt, auth, version):
    # Add id to statement if not present
    if not 'id' in stmt:
        stmt['id'] = str(uuid.uuid1())

    # Add version to statement if not present
    if not 'version' in stmt:
        stmt['version'] = version

    # Convert context activities to list if dict
    if 'context' in stmt and 'contextActivities' in stmt['context']:
        for k, v in stmt['context']['contextActivities'].items():
            if isinstance(v, dict):
                stmt['context']['contextActivities'][k] = [v]

    # Convert context activities to list if dict (for substatements)
    if 'objectType' in stmt['object'] and stmt['object']['objectType'] == 'SubStatement':
        if 'context' in stmt['object'] and 'contextActivities' in stmt['object']['context']:
            for k, v in stmt['object']['context']['contextActivities'].items():
                if isinstance(v, dict):
                    stmt['object']['context']['contextActivities'][k] = [v]

    # Add stored time
    stmt['stored'] = str(datetime.utcnow().replace(tzinfo=utc).isoformat())

    # Add stored as timestamp if timestamp not present
    if not 'timestamp' in stmt:
        stmt['timestamp'] = stmt['stored']

    # Copy full statement and send off to StatementManager to save
    full_stmt = copy.deepcopy(stmt)
    st = StatementManager(stmt, auth, full_stmt).model_object
    return st.statement_id

def process_body(stmts, auth, version):
    return [process_statement(st, auth, version) for st in stmts]

def check_activity_metadata(stmts):
    activity_ids = list(Activity.objects.filter(object_of_statement__statement_id__in=stmts).values_list('activity_id', flat=True).distinct())
    [get_activity_metadata(a_id) for a_id in activity_ids]

# Retrieve JSON data from ID
def get_activity_metadata(act_id):
    act_url_data = {}
    # See if id resolves
    try:
        req = urllib2.Request(act_id)
        req.add_header('Accept', 'application/json, */*')
        act_resp = urllib2.urlopen(req, timeout=settings.ACTIVITY_ID_RESOLVE_TIMEOUT)
    except Exception:
        # Doesn't resolve-hopefully data is in payload
        pass
    else:
        # If it resolves then try parsing JSON from it
        try:
            act_url_data = json.loads(act_resp.read())
        except Exception:
            # Resolves but no data to retrieve - this is OK
            pass

        # If there was data from the URL
        if act_url_data:
            valid_url_data = True
            # Have to validate new data given from URL
            try:
                fake_activity = {"id": act_id, "definition": act_url_data}
                validator = StatementValidator()
                validator.validate_activity(fake_activity)
            except Exception, e:
                valid_url_data = False
            except ParamError, e:
                valid_url_data = False

            if valid_url_data:
                update_activity_definition(fake_activity)

@transaction.commit_on_success
def update_activity_definition(act):
    # Try to get canonical activity by id
    try:
        activity = Activity.objects.get(activity_id=act['id'], canonical_version=True)
    except Activity.DoesNotExist:
        # Could not exist yet
        pass
    # If the activity already exists in the db
    else:
        # If there is a name in the IRI act definition add it to what already exists
        if 'name'in act['definition']:
            activity.activity_definition_name = dict(activity.activity_definition_name.items() + act['definition']['name'].items())
        # If there is a description in the IRI act definition add it to what already exists
        if 'description' in act['description']:
            activity.activity_definition_description = dict(activity.activity_definition_description.items() + act['definition']['description'].items())

        activity.activity_definition_type = act['definition'].get('type', '')
        activity.activity_definition_moreInfo = act['definition'].get('moreInfo', '')
        activity.activity_definition_interactionType = act['definition'].get('interactionType', '')
        activity.activity_definition_extensions = act['definition'].get('extensions', {})
        activity.activity_definition_crpanswers = act['definition'].get('correctResponsesPattern', {})
        activity.activity_definition_choices = act['definition'].get('choices', {})
        activity.activity_definition_sources = act['definition'].get('source', {}) 
        activity.activity_definition_targets = act['definition'].get('target', {})
        activity.activity_definition_steps = act['definition'].get('steps', {})
        activity.activity_definition_scales = act['definition'].get('scale', {})
        activity.save()

def process_complex_get(req_dict):
    mime_type = "application/json"
    # Parse out params into single dict-GET data not in body
    param_dict = {}
    try:
        param_dict = req_dict['body']
        if not isinstance(param_dict, dict):
            param_dict = convert_to_dict(param_dict)
    except KeyError:
        pass # no params in the body    
    param_dict.update(req_dict['params'])
    format = param_dict['format']
    
    # Set language if one pull from req_dict since language is from a header, not an arg 
    language = None
    if 'headers' in req_dict and ('format' in param_dict and param_dict['format'] == "canonical"):
        if 'language' in req_dict['headers']:
            language = req_dict['headers']['language']
        else:
            language = settings.LANGUAGE_CODE

    # If auth is in req dict, add it to param dict
    if 'auth' in req_dict:
        param_dict['auth'] = req_dict['auth']

    # Get limit if one
    limit = None
    if 'params' in req_dict and 'limit' in req_dict['params']:
        limit = int(req_dict['params']['limit'])
    elif 'body' in req_dict and 'limit' in req_dict['body']:
        limit = int(req_dict['body']['limit'])

    # See if attachments should be included
    try:
        attachments = req_dict['params']['attachments']
    except Exception:
        attachments = False

    # Create returned stmt list from the req dict
    stmt_result = complex_get(param_dict, limit, language, format, attachments)
    
    # Get the length of the response - make sure in string format to count every character
    if isinstance(stmt_result, dict):
        content_length = len(json.dumps(stmt_result))
    else:
        content_length = len(stmt_result)

    # If attachments=True in req_dict then include the attachment payload and return different mime type
    if attachments:
        stmt_result, mime_type, content_length = build_response(stmt_result)
        resp = HttpResponse(stmt_result, content_type=mime_type, status=200)
    # Else attachments are false for the complex get so just dump the stmt_result
    else:
        if isinstance(stmt_result, dict):
            stmt_result = json.dumps(stmt_result)

        resp = HttpResponse(stmt_result, content_type=mime_type, status=200)    
    return resp, content_length

def statements_post(req_dict):
    auth = req_dict['auth']
    # If single statement, put in list
    if isinstance(req_dict['body'], dict):
        body = [req_dict['body']]
    else:
        body = req_dict['body']

    stmt_responses = process_body(body, auth, req_dict['headers']['X-Experience-API-Version'])
    check_activity_metadata(stmt_responses)
    return HttpResponse(json.dumps([st for st in stmt_responses]), mimetype="application/json", status=200)

def statements_put(req_dict):
    auth = req_dict['auth']
    # Since it is single stmt put in list
    stmt_responses = process_body([req_dict['body']], auth, req_dict['headers']['X-Experience-API-Version'])
    check_activity_metadata(stmt_responses)
    return HttpResponse("No Content", status=204)

def statements_more_get(req_dict):
    stmt_result, attachments = get_more_statement_request(req_dict['more_id'])     

    if isinstance(stmt_result, dict):
        content_length = len(json.dumps(stmt_result))
    else:
        content_length = len(stmt_result)
    mime_type = "application/json"

    # If there are attachments, include them in the payload
    if attachments:
        stmt_result, mime_type, content_length = build_response(stmt_result)
        resp = HttpResponse(stmt_result, content_type=mime_type, status=200)
    # If not, just dump the stmt_result
    else:
        if isinstance(stmt_result, basestring):
            resp = HttpResponse(stmt_result, content_type=mime_type, status=200)
        else:
            resp = HttpResponse(json.dumps(stmt_result), content_type=mime_type, status=200)
    
    # Add consistent header and set content-length
    try:
        resp['X-Experience-API-Consistent-Through'] = str(Statement.objects.latest('stored').stored)
    except:
        resp['X-Experience-API-Consistent-Through'] = str(datetime.now())
    resp['Content-Length'] = str(content_length)
    
    # If it's a HEAD request
    if req_dict['method'].lower() != 'get':
        resp.body = ''

    return resp

def statements_get(req_dict):
    stmt_result = {}
    mime_type = "application/json"
    # If statementId is in req_dict then it is a single get - can still include attachments
    # or have a different format
    if 'statementId' in req_dict:     
        if req_dict['params']['attachments']:
            resp, content_length = process_complex_get(req_dict)
        else:
            st = Statement.objects.get(statement_id=req_dict['statementId'])
            
            stmt_result = json.dumps(st.to_dict(format=req_dict['params']['format']))
            resp = HttpResponse(stmt_result, content_type=mime_type, status=200)
            content_length = len(stmt_result)
    # Complex GET
    else:
        resp, content_length = process_complex_get(req_dict)
        
    # Set consistent through and content length headers for all responses
    try:
        resp['X-Experience-API-Consistent-Through'] = str(Statement.objects.latest('stored').stored)
    except:
        resp['X-Experience-API-Consistent-Through'] = str(datetime.now())
    
    resp['Content-Length'] = str(content_length) 

    # If it's a HEAD request
    if req_dict['method'].lower() != 'get':
        resp.body = ''

    return resp

def build_response(stmt_result):
    sha2s = []
    mime_type = "application/json"
    if isinstance(stmt_result, dict):
        statements = stmt_result['statements']
    else:
        statements = json.loads(stmt_result)['statements']

    # Iterate through each attachment in each statement
    for stmt in statements:
        if 'attachments' in stmt:
            for attachment in stmt['attachments']:
                if 'sha2' in attachment:
                    # If there is a sha2-retrieve the StatementAttachment object and add the payload to sha2s
                    att_object = StatementAttachment.objects.get(sha2=attachment['sha2'])
                    sha2s.append((attachment['sha2'], att_object.payload, att_object.contentType))    
    # If attachments have payloads
    if sha2s:
        # Create multipart message and attach json message to it
        string_list =[]
        line_feed = "\r\n"
        boundary = "======ADL_LRS======"
        string_list.append(line_feed + "--" + boundary + line_feed)
        string_list.append("Content-Type:application/json" + line_feed + line_feed)
        if isinstance(stmt_result, dict):
            string_list.append(json.dumps(stmt_result) + line_feed)
        else:
            string_list.append(stmt_result + line_feed)
        for sha2 in sha2s:
            string_list.append("--" + boundary + line_feed)
            string_list.append("Content-Type:%s" % str(sha2[2]) + line_feed)
            string_list.append("Content-Transfer-Encoding:binary" + line_feed)
            string_list.append("X-Experience-API-Hash:" + str(sha2[0]) + line_feed + line_feed)

            chunks = []
            try:
                # Default chunk size is 64kb
                for chunk in sha2[1].chunks():
                    decoded_data = b64decode(chunk)
                    chunks.append(decoded_data)
            except OSError:
                raise OSError(2, "No such file or directory", sha2[1].name.split("/")[1])

            string_list.append("".join(chunks) + line_feed)
        
        string_list.append("--" + boundary + "--") 
        mime_type = "multipart/mixed; boundary=" + boundary
        attachment_body = "".join([s for s in string_list])
        return attachment_body, mime_type, len(attachment_body)
    # Has attachments but no payloads so just dump the stmt_result
    else:
        if isinstance(stmt_result, dict):
            res = json.dumps(stmt_result)
            return res, mime_type, len(res)
        else:
            return stmt_result, mime_type, len(stmt_result)

def activity_state_post(req_dict):
    # test ETag for concurrency
    agent = req_dict['params']['agent']
    a = Agent.objects.retrieve_or_create(**agent)[0]
    actstate = ActivityStateManager(a)
    actstate.post_state(req_dict)
    return HttpResponse("", status=204)

def activity_state_put(req_dict):
    # test ETag for concurrency
    agent = req_dict['params']['agent']
    a = Agent.objects.retrieve_or_create(**agent)[0]
    actstate = ActivityStateManager(a)
    actstate.put_state(req_dict)
    return HttpResponse("", status=204)

def activity_state_get(req_dict):
    # add ETag for concurrency
    state_id = req_dict['params'].get('stateId', None)
    activity_id = req_dict['params']['activityId']
    agent = req_dict['params']['agent']
    a = Agent.objects.retrieve_or_create(**agent)[0]
    registration = req_dict['params'].get('registration', None)
    actstate = ActivityStateManager(a)
    # state id means we want only 1 item
    if state_id:
        resource = actstate.get_state(activity_id, registration, state_id)
        if resource.state:
            response = HttpResponse(resource.state.read(), content_type=resource.content_type)
        else:
            response = HttpResponse(resource.json_state, content_type=resource.content_type)
        response['ETag'] = '"%s"' % resource.etag
    # no state id means we want an array of state ids
    else:
        since = req_dict['params'].get('since', None)
        resource = actstate.get_state_ids(activity_id, registration, since)
        response = HttpResponse(json.dumps([k for k in resource]), content_type="application/json")
    
    # If it's a HEAD request
    if req_dict['method'].lower() != 'get':
        response.body = ''

    return response

def activity_state_delete(req_dict):
    agent = req_dict['params']['agent']
    a = Agent.objects.retrieve_or_create(**agent)[0]
    actstate = ActivityStateManager(a)
    # Delete state
    actstate.delete_state(req_dict)
    return HttpResponse('', status=204)

def activity_profile_post(req_dict):
    #Instantiate ActivityProfile
    ap = ActivityProfileManager()
    #Put profile and return 204 response
    ap.post_profile(req_dict)
    return HttpResponse('', status=204)

def activity_profile_put(req_dict):
    #Instantiate ActivityProfile
    ap = ActivityProfileManager()
    #Put profile and return 204 response
    ap.put_profile(req_dict)
    return HttpResponse('', status=204)

def activity_profile_get(req_dict):
    # Instantiate ActivityProfile
    ap = ActivityProfileManager()
    # Get profileId and activityId
    profileId = req_dict['params'].get('profileId', None) if 'params' in req_dict else None
    activityId = req_dict['params'].get('activityId', None) if 'params' in req_dict else None
    
    #If the profileId exists, get the profile and return it in the response
    if profileId:
        resource = ap.get_profile(profileId, activityId)
        if resource.profile:
            try:
                response = HttpResponse(resource.profile.read(), content_type=resource.content_type)
            except IOError:
                response = HttpResponseNotFound("Error reading file, could not find: %s" % profileId)
        else:
            response = HttpResponse(resource.json_profile, content_type=resource.content_type)            
        response['ETag'] = '"%s"' % resource.etag
        return response

    #Return IDs of profiles stored since profileId was not submitted
    since = req_dict['params'].get('since', None) if 'params' in req_dict else None
    resource = ap.get_profile_ids(activityId, since)
    response = HttpResponse(json.dumps([k for k in resource]), content_type="application/json")
    response['since'] = since
    
    # If it's a HEAD request
    if req_dict['method'].lower() != 'get':
        resp.body = ''

    return response

def activity_profile_delete(req_dict):
    #Instantiate activity profile
    ap = ActivityProfileManager()
    # Delete profile and return success
    ap.delete_profile(req_dict)
    return HttpResponse('', status=204)

def activities_get(req_dict):
    activityId = req_dict['params']['activityId']
    act = Activity.objects.get(activity_id=activityId, canonical_version=True)    
    return_act = json.dumps(act.to_dict())    
    resp = HttpResponse(return_act, mimetype="application/json", status=200)
    resp['Content-Length'] = str(len(return_act))
    
    # If it's a HEAD request
    if req_dict['method'].lower() != 'get':
        resp.body = ''

    return resp

def agent_profile_post(req_dict):
    # test ETag for concurrency
    agent = req_dict['params']['agent']
    a = Agent.objects.retrieve_or_create(**agent)[0]
    ap = AgentProfileManager(a)
    ap.post_profile(req_dict)

    return HttpResponse("", status=204)

def agent_profile_put(req_dict):
    # test ETag for concurrency
    agent = req_dict['params']['agent']
    a = Agent.objects.retrieve_or_create(**agent)[0]
    ap = AgentProfileManager(a)
    ap.put_profile(req_dict)

    return HttpResponse("", status=204)

def agent_profile_get(req_dict):
    # add ETag for concurrency
    agent = req_dict['params']['agent']
    a = Agent.objects.retrieve_or_create(**agent)[0]
    ap = AgentProfileManager(a)

    profileId = req_dict['params'].get('profileId', None) if 'params' in req_dict else None
    if profileId:
        resource = ap.get_profile(profileId)
        if resource.profile:
            response = HttpResponse(resource.profile.read(), content_type=resource.content_type)
        else:
            response = HttpResponse(resource.json_profile, content_type=resource.content_type)            
        response['ETag'] = '"%s"' % resource.etag
        return response

    since = req_dict['params'].get('since', None) if 'params' in req_dict else None
    resource = ap.get_profile_ids(since)
    response = HttpResponse(json.dumps([k for k in resource]), content_type="application/json")
    
    # If it's a HEAD request
    if req_dict['method'].lower() != 'get':
        resp.body = ''

    return response

def agent_profile_delete(req_dict):
    agent = req_dict['params']['agent']
    a = Agent.objects.retrieve_or_create(**agent)[0]
    profileId = req_dict['params']['profileId']
    ap = AgentProfileManager(a)
    ap.delete_profile(profileId)

    return HttpResponse('', status=204)

def agents_get(req_dict):
    a = Agent.objects.get(**req_dict['agent_ifp'])    
    agent_data = json.dumps(a.to_dict_person())
    resp = HttpResponse(agent_data, mimetype="application/json")
    resp['Content-Length'] = str(len(agent_data))
    
    # If it's a HEAD request
    if req_dict['method'].lower() != 'get':
        resp.body = ''
            
    return resp
