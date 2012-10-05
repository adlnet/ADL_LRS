import json
from lrs import models
from django.contrib.auth import authenticate
import base64
import ast
import pdb

import pprint

def basic_http_auth(f):
    def wrap(r, *args, **kwargs):
        # pdb.set_trace()
        if r['method'] == 'POST' and not r['CONTENT_TYPE'] == 'application/json':
            return f(r, *args, **kwargs)
        else:
            if 'Authorization' in r:
                authtype, auth = r['Authorization'].split(' ')
                auth = base64.b64decode(auth)
                username, password = auth.split(':')
                user = authenticate(username=username, password=password)

                if user is not None:
                    r['user'] = user
                    return f(r, *args, **kwargs)
                    
            raise NotAuthorizedException("Auth Required")
        
    return wrap

class NotAuthorizedException(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)

@basic_http_auth
def statements_post(r_dict):
    if "application/json" not in r_dict['CONTENT_TYPE']:
        r_dict['method'] = 'GET'
    return r_dict

def statements_get(r_dict):
    return r_dict

def check_for_existing_statementId(stmtID):
    exists = False
    stmt = models.statement.objects.filter(statement_id=stmtID)
    if stmt:
        exists = True
    return exists

def check_for_no_other_params_supplied(query_dict):
    supplied = True
    if len(query_dict) <= 1:
        supplied = False
    return supplied

@basic_http_auth
def statements_put(r_dict):
    try:
        if isinstance(r_dict['body'], str):
            r_dict['body'] = ast.literal_eval(r_dict['body'])
        statement_id = r_dict['statementId']
    except KeyError:
        raise ParamError("Error -- statements - method = %s, but statementId paramater is missing" % r_dict['method'])
    
    if check_for_existing_statementId(statement_id):
        raise ParamConflictError("StatementId conflict")

    if not check_for_no_other_params_supplied(r_dict['body']):
        raise NoParamsError("No Content supplied")
    return r_dict


@basic_http_auth
def activity_state_put(r_dict):
    try:
        r_dict['activityId']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but activityId parameter is missing.." % r_dict['method'])
    try:
        r_dict['actor']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but actor parameter is missing.." % r_dict['method'])
    try:
        r_dict['stateId']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but stateId parameter is missing.." % r_dict['method'])
    
    if 'body' not in r_dict:
        raise ParamError("Could not find the profile")
    r_dict['state'] = r_dict.pop('body')
    return r_dict


def activity_state_get(r_dict):
    try:
        r_dict['activityId']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but activityId parameter is missing.." % r_dict['method'])
    try:
        r_dict['actor']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but actor parameter is missing.." % r_dict['method'])
    return r_dict


@basic_http_auth
def activity_state_delete(r_dict):
    try:
        r_dict['activityId']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but activityId parameter is missing.." % r_dict['method'])
    try:
        r_dict['actor']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but actor parameter is missing.." % r_dict['method'])
    return r_dict
  
        
@basic_http_auth
def activity_profile_put(r_dict):
    try:
        r_dict['activityId']
    except KeyError:
        raise ParamError("Error -- activity_profile - method = %s, but activityId parameter missing.." % r_dict['method'])
    
    try:
        r_dict['profileId']
    except KeyError:
        raise ParamError("Error -- activity_profile - method = %s, but profileId parameter missing.." % r_dict['method'])
    
    if 'body' not in r_dict:
        raise ParamError("Could not find the profile")

    bdy = r_dict.pop('body')
    r_dict['profile'] = bdy #json.dumps([i.values()[::-1] for i in bdy])
    
    return r_dict

def activity_profile_get(r_dict):
    try:
        r_dict['activityId']
    except KeyError:
         raise ParamError("Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % r_dict['method'])
    return r_dict


@basic_http_auth
def activity_profile_delete(r_dict):
    try:
        r_dict['activityId']
    except KeyError:
         raise ParamError("Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % r_dict['method'])
    try:
        r_dict['profileId']
    except KeyError:
         raise ParamError("Error -- activity_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % r_dict['method'])
    return r_dict


def activities_get(r_dict):
    try:
        r_dict['activityId']
    except KeyError:
        raise ParamError("Error -- activities - method = %s, but activityId parameter is missing" % r_dict['method'])
    return r_dict

@basic_http_auth
def actor_profile_put(r_dict):
    try:
        r_dict['actor']
    except KeyError:
        raise ParamError("Error -- actor_profile - method = %s, but actor parameter missing.." % r_dict['method'])
    try:
        r_dict['profileId']
    except KeyError:
        raise ParamError("Error -- actor_profile - method = %s, but profileId parameter missing.." % r_dict['method'])
    
    if 'body' not in r_dict:
        raise ParamError("Could not find the profile")
    r_dict['profile'] = r_dict.pop('body')
    return r_dict


def actor_profile_get(r_dict):
    try:
        r_dict['actor']
    except KeyError:
        raise ParamError("Error -- actor_profile - method = %s, but actor parameter missing.. the actor parameter is required" % r_dict['method'])
    return r_dict


@basic_http_auth
def actor_profile_delete(r_dict):
    try:
        r_dict['actor']
    except KeyError:
        raise ParamError("Error -- actor_profile - method = %s, but no actor parameter.. the actor parameter is required" % r_dict['method'])
    try:
        r_dict['profileId']
    except KeyError:
        raise ParamError("Error -- actor_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % r_dict['method'])
    return r_dict


def actors_get(r_dict):
    try:
        r_dict['actor']
    except KeyError:
        raise ParamError("Error -- actors url, but no actor parameter.. the actor parameter is required")
    return r_dict


class ParamError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)

class ParamConflictError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)

class NoParamsError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)