from copy import deepcopy # runs slow.. we should only use if necessary
import json
from lrs.util import etag
from django.http import MultiPartParser, HttpResponse
from django.contrib.auth import authenticate
import StringIO
import base64
import pdb

def basic_http_auth(f):
    def wrap(request, *args, **kwargs):
        # pdb.set_trace()
        if request.method == 'POST' and not request.META['CONTENT_TYPE'] == 'application/json':
            return f(request, *args, **kwargs)
        else:
            if request.META.get('HTTP_AUTHORIZATION', False):

                authtype, auth = request.META['HTTP_AUTHORIZATION'].split(' ')
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
    # pdb.set_trace()
    req_dict = {}

    if request.META['CONTENT_TYPE'] == "application/json":
        body = request.body
        jsn = body.replace("'", "\"")
        raw = request.raw_post_data.replace("'", "\"")

        # spec not quite clear, assuming if the type is json it's a real POST
        req_dict = get_dict(request)
        return req_dict, request.user
    else:
        return request.POST.dict()

def statements_get(request):
    req_dict = {}
    postParams = ['verb', 'object', 'registration', 'context', 'actor', 'since', 'until', 'limit', 'authoritative', 'sparse', 'instructor']
    sentParams = [x for x in request.GET]
    complexRequest = False
    req_dict['body'] = deepcopy(request.GET.dict())
    complexRequest = any(x in sentParams for x in postParams)
    
    if complexRequest:
        req_dict['complex'] = True
    else:
        try:
            req_dict['body']['statementId']
            req_dict['complex'] = False
        except KeyError:
            raise ParamError("Error -- statements - method = %s, but statementId parameter is missing" % request.method)
    return req_dict

@basic_http_auth
def statements_put(request):
    req_dict = get_dict(request)
    try:
        req_dict['body']['statementId']
    except KeyError:
        raise ParamError("Error -- statements - method = %s, but statementId paramater is missing" % request.method)
    return req_dict, request.user


@basic_http_auth
def activity_state_put(request):
    req_dict = get_dict(request)
    try:
        req_dict['activityId']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but activityId parameter is missing.." % request.method)
    try:
        req_dict['actor']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but actor parameter is missing.." % request.method)
    try:
        req_dict['stateId']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but stateId parameter is missing.." % request.method)
    
    if request.raw_post_data == '':
        raise ParamError("Could not find the activity state document")
    req_dict['state'] = request.raw_post_data
    # this is stupid but unit tests come back as 'updated'
    # and as 'HTTP_UPDATED' when used tested from python requests
    req_dict['updated'] = request.META.get('HTTP_UPDATED', None)
    if not req_dict['updated']:
        req_dict['updated'] = request.META.get('updated', None)
    req_dict['CONTENT_TYPE'] = request.META.get('CONTENT_TYPE', '')
    req_dict['ETAG'] = etag.get_etag_info(request, required=False)
    return req_dict


def activity_state_get(request):
    try:
        request.GET['activityId']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but activityId parameter is missing.." % request.method)
    try:
        request.GET['actor']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but actor parameter is missing.." % request.method)
    return request.GET


@basic_http_auth
def activity_state_delete(request):
    try:
        request.GET['activityId']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but activityId parameter is missing.." % request.method)
    try:
        request.GET['actor']
    except KeyError:
        raise ParamError("Error -- activity_state - method = %s, but actor parameter is missing.." % request.method)
    return request.GET
  
        
@basic_http_auth
def activity_profile_put(request):
    #Get request dictionary
    req_dict = get_dict(request)

    #Not using request.GET.get('param', 'default val') cuz activityId and profileId are mandatory
    try: 
        req_dict['activityId']
    except KeyError:
        raise ParamError("Error -- activity_profile - method = %s, but activityId parameter missing.." % request.method)
    
    try:
        req_dict['profileId']
    except KeyError:
        raise ParamError("Error -- activity_profile - method = %s, but profileId parameter missing.." % request.method)
    
    #Check for profile
    if request.raw_post_data == '':
        raise ParamError("Could not find the profile")
    
    req_dict['profile'] = request.raw_post_data

    # This is stupid but unit tests come back as 'updated'
    # and as 'HTTP_UPDATED' when used tested from python requests
    req_dict['updated'] = request.META.get('HTTP_UPDATED', None)
    
    if not req_dict['updated']:
        req_dict['updated'] = request.META.get('updated', None)
    
    #Set content type and etag
    req_dict['CONTENT_TYPE'] = request.META.get('CONTENT_TYPE', '')
    req_dict['ETAG'] = etag.get_etag_info(request, required=False)
    
    return req_dict

def activity_profile_get(request):
    #Parse activityId since it is the only param always required
    try:
        request.GET['activityId']
    except KeyError:
         raise ParamError("Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % request.method)
    return request.GET


@basic_http_auth
def activity_profile_delete(request):
    #Parse activityId and profileId since both are required
    try:
        request.GET['activityId']
    except KeyError:
         raise ParamError("Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % request.method)
    try:
        request.GET['profileId']
    except KeyError:
         raise ParamError("Error -- activity_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % request.method)
    return request.GET


def activities_get(request):
    try:
        request.GET['activityId']
    except KeyError:
        raise ParamError("Error -- activities - method = %s, but activityId parameter is missing" % request.method)
    return request.GET

#import pprint
@basic_http_auth
def actor_profile_put(request):
    req_dict = get_dict(request)

    try: # not using request.GET.get('param', 'default val') cuz actor is mandatory
        req_dict['actor']
    except KeyError:
        raise ParamError("Error -- actor_profile - method = %s, but actor parameter missing.." % request.method)
    try:
        req_dict['profileId']
    except KeyError:
        raise ParamError("Error -- actor_profile - method = %s, but profileId parameter missing.." % request.method)
    
    if request.raw_post_data == '':
        raise ParamError("Could not find the profile")

    req_dict['profile'] = request.raw_post_data

    # this is stupid but unit tests come back as 'updated'
    # and as 'HTTP_UPDATED' when used tested from python requests
    req_dict['updated'] = request.META.get('HTTP_UPDATED', None)

    if not req_dict['updated']:
        req_dict['updated'] = request.META.get('updated', None)

    req_dict['CONTENT_TYPE'] = request.META.get('CONTENT_TYPE', '')
    req_dict['ETAG'] = etag.get_etag_info(request, required=False)

    return req_dict


def actor_profile_get(request):
    try: 
        request.GET['actor']
    except KeyError:
        raise ParamError("Error -- actor_profile - method = %s, but actor parameter missing.. the actor parameter is required" % request.method)
    return request.GET


@basic_http_auth
def actor_profile_delete(request):
    try: 
        request.GET['actor']
    except KeyError:
        raise ParamError("Error -- actor_profile - method = %s, but no actor parameter.. the actor parameter is required" % request.method)
    try:
        request.GET['profileId']
    except KeyError:
        raise ParamError("Error -- actor_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % request.method)
    return request.GET


def actors_get(request):
    try: 
        request.GET['actor']
    except KeyError:
        raise ParamError("Error -- actors url, but no actor parameter.. the actor parameter is required")
    return request.GET


def get_dict(request):
    # puts seem to have the parameters in the body..
    if request.method == 'POST' or request.method == 'PUT':
        ret_dict = {}
        if request.GET: # looking for parameters
            ret_dict.update(request.GET.dict())
        if 'multipart/form-data' in request.META['CONTENT_TYPE']:
            ret_dict.update(request.POST.dict())
            parser = MultiPartParser(request.META, StringIO.StringIO(request.raw_post_data),request.upload_handlers)
            post, files = parser.parse()
            ret_dict['files'] = files
        else:
            if request.body:
                body = request.body
                jsn = body.replace("'", "\"")
                ret_dict['body'] = json.loads(jsn)
        
        return ret_dict
    return {}

class ParamError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)
