from copy import deepcopy # runs slow.. we should only use if necessary
import json
from lrs.util import etag
from django.http import MultiPartParser
import StringIO

def statements_post(request):
    req_dict = {}
    if request.GET: # looking for parameters
        req_dict.update(request.GET.dict()) # dict() is new to django 1.4

    body = request.body
    jsn = body.replace("'", "\"")
    # spec not quite clear, i'm assuming if the type is json it's a real POST
    if request.META['CONTENT_TYPE'] == 'application/json; charset=UTF-8': 
        req_dict['body'] = deepcopy(json.loads(jsn))
        req_dict['is_get'] = False
    else: # if not, then it must be form data
        valid_params = ['verb','object','registration','context','actor','since','until','limit','authoritative','sparse','instructor']
        try:
            req_dict.update(json.loads(jsn))
        except:
            req_dict.update(request.POST.dict())
        # test if one of the request keys is a valid paramter
        if not [k for k,v in req_dict.items() if k in valid_params]:
            raise ParamError("Error -- could not find a valid parameter")
        req_dict['is_get'] = True
    return req_dict


def statements_get(request):
    try:
        request.GET['statementId']
    except KeyError:
        raise ParamError("Error -- statements - method = %s, but statementId parameter is missing" % request.method)
    return request.GET


def statements_put(request):
    req_dict = get_dict(request)
    try:
        req_dict['statementId']
    except KeyError:
        raise ParamError("Error -- statements - method = %s, but statementId paramater is missing" % request.method)
    return req_dict


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
  
        
def activity_profile_put(request):
    req_dict = get_dict(request)
    try: # not using request.GET.get('param', 'default val') cuz activityId is mandatory
        req_dict['activityId']
    except KeyError:
        raise ParamError("Error -- activity_profile - method = %s, but activityId parameter missing.." % request.method)
    try:
        req_dict['profileId']
    except KeyError:
        raise ParamError("Error -- activity_profile - method = %s, but profileId parameter missing.." % request.method)
    try:
        req_dict['body'] = request.body
    except:
        raise ParamError("Error -- no profile in request body")
    return req_dict


def activity_profile_get(request):
    try: # not using request.GET.get('param', 'default val') cuz activityId is mandatory
        request.GET['activityId']
    except KeyError:
         raise ParamError("Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % request.method)
    return request.GET


def activity_profile_delete(request):
    try: # not using request.GET.get('param', 'default val') cuz activityId is mandatory
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
    #try:
    #    thefile = req_dict['files']['file']
    #    req_dict['filename'] = thefile.name
    #    req_dict['profile'] = thefile.read()
    #except:
    #    req_dict['profile'] = req_dict.get('body', '')
    #    if not req_dict['profile']:
    #        raise ParamError("Could not find the profile")
    
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
