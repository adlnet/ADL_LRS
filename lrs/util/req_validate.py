from copy import deepcopy # runs slow.. we should only use if necessary
import json
from lrs.util import etag
from django.http import MultiPartParser, HttpResponse
from django.contrib.auth import authenticate
import StringIO
import base64
import ast
import pdb

def basic_http_auth(f):
    def wrap(request, *args, **kwargs):
        if request.method == 'POST' and not request.META['CONTENT_TYPE'] == 'application/json':
            return f(request, *args, **kwargs)
        else:
            if 'HTTP_AUTHORIZATION' in request.META or 'Authorization' in request.META:
                try:
                    authtype, auth = request.META['HTTP_AUTHORIZATION'].split(' ')
                except KeyError:
                    authtype, auth = request.META['Authorization'].split(' ')
                auth = base64.b64decode(auth)
                username, password = auth.split(':')
                user = authenticate(username=username, password=password)

                if user is not None:
                    request.user = user
                    return f(request, *args, **kwargs)
                    
            raise NotAuthorizedException("Auth Required")
        
    return wrap

class NotAuthorizedException(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)

@basic_http_auth
def statements_post(request):
    # TODO: more elegant way of doing this?
    req_dict = {}

    if request.META['CONTENT_TYPE'] == "application/json":
        body = request.body
        jsn = body.replace("'", "\"")
        raw = request.raw_post_data.replace("'", "\"")

        # spec not quite clear, assuming if the type is json it's a real POST
        req_dict = get_dict(request)
        return req_dict, request.user
    else:
        return ast.literal_eval(request.raw_post_data)

def statements_get(request):
    # pdb.set_trace()
    return request.GET

@basic_http_auth
def statements_put(request):
    req_dict = get_dict(request)
    try:
        req_dict['body']['statementId']
    except KeyError:
        raise ParamError("Error -- statements - method = %s, but statementId paramater is missing" % request.method)
    return req_dict, request.user


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
    
    if 'raw_post_data' not in r_dict:
        raise ParamError("Could not find the profile")
    r_dict['state'] = r_dict.pop('raw_post_data')
    return req_dict


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
    
    if 'raw_post_data' not in r_dict:
        raise ParamError("Could not find the profile")
    r_dict['profile'] = r_dict.pop('raw_post_data')
    
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
    
    if 'raw_post_data' not in r_dict:
        raise ParamError("Could not find the profile")
    r_dict['profile'] = r_dict.pop('raw_post_data')
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
