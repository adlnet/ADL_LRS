from django.http import HttpResponse
from lrs import objects, models
from lrs.util import etag
import json
import sys
from os import path
import pdb
from functools import wraps
from lrs.objects import Actor, Activity, ActivityState, ActivityProfile, Statement
from datetime import datetime
import pytz

def statements_post(req_dict):
    #TODO: more elegant way of doing this?
    # pdb.set_trace()
    if type(req_dict) is dict:
        returnList = complexGet(req_dict)
        return HttpResponse(returnList, mimetype="application/json", status=200)
    else:
        stmtResponses = []
        if not type(req_dict[0]['body']) is list:
            stmt = Statement.Statement(req_dict[0]['body'], auth=req_dict[1]).statement
            stmtResponses.append(str(stmt.id))
        else:
            for st in req_dict[0]['body']:
                stmt = Statement.Statement(st, auth=req_dict[1]).statement
                stmtResponses.append(str(stmt.statement_id))
        return HttpResponse("StatementID(s) = %s" % stmtResponses, status=200)
        
def statements_put(req_dict):
    statementId = req_dict[0]['body']['statementId']
    try:
        stmt = models.statement.objects.get(statement_id=statementId)
    except models.statement.DoesNotExist:
        stmt = Statement.Statement(req_dict[0]['body'], auth=req_dict[1]).statement        
        return HttpResponse("StatementID = %s" % statementId, status=200)
    else:
        return HttpResponse("Error: %s already exists" % statementId, status=204)
     
def statements_get(req_dict):
    # pdb.set_trace()
    if req_dict['complex']:
        returnList = complexGet(req_dict['body'])
        return HttpResponse(returnList, mimetype="application/json", status=200)
    else:
        statementId = req_dict['body']['statementId']
        st = Statement.Statement(statement_id=statementId, get=True)
        data = st.get_full_statement_json()
        return HttpResponse(st.get_full_statement_json(), mimetype="application/json")

def convertToUTC(timestr):
    # Strip off TZ info
    timestr = timestr[:timestr.rfind('+')]
    # Convert to date_object (directive for parsing TZ out is buggy, which is why we do it this way)
    date_object = datetime.strptime(timestr, '%Y-%m-%dT%H:%M:%S.%f')
    # Localize TZ to UTC since everything is being stored in DB as UTC
    date_object = pytz.timezone("UTC").localize(date_object)
    return date_object

def complexGet(req_dict):
    
    args = {}

    for k,v in req_dict.items():
        if k.lower() == 'verb':
            args[k] = v 
        elif k.lower() == 'since':
            date_object = convertToUTC(v)
            args['stored__gt'] = date_object
        elif k.lower() == 'until':
            date_object = convertToUTC(v)
            args['stored__lte'] = date_object

    if 'object' in req_dict:
        pdb.set_trace()
        objectData = req_dict['object']        
        try:
            objectData = json.loads(objectData) 
        except Exception, e:
            objectData = json.loads(objectData.replace("'",'"'))
 
        if objectData['objectType'].lower() == 'activity':
            activity = models.activity.objects.get(activity_id=objectData['id'])
            args['stmt_object'] = activity
        elif objectData['objectType'].lower() == 'agent' or objectData['objectType'].lower() == 'person':
            agent = Actor(objectData).agent
            args['stmt_object'] = agent
    
    else:
        objectData = req_dict['object']        
        try:
            objectData = json.loads(objectData) 
        except Exception, e:
            objectData = json.loads(objectData.replace("'",'"'))
        activity = models.activity.objects.get(activity_id=objectData['id'])
        args['stmt_object'] = activity        

    # Retrieve statements from DB
    stmt_list = models.statement.objects.filter(**args).order_by('-stored')

    full_stmt_list = []

    # For each stmt convert to our Statement class and retrieve all json
    for stmt in stmt_list:
        stmt = Statement.Statement(statement_id=stmt.statement_id, get=True)
        full_stmt_list.append(stmt.get_full_statement_json())

    return full_stmt_list
        # return HttpResponse(rl.replace(r"\"", "'"), mimetype="application/json", status=200)

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
    # pdb.set_trace()
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
