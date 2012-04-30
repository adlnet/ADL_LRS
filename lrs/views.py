from django.http import HttpResponse, Http404
from django.http import QueryDict
from django.views.decorators.http import require_http_methods, require_GET, require_POST
import json
from urlparse import parse_qs, parse_qsl

def home(request):
    return HttpResponse("you hit the home url of the ADL example LRS")


def statements(request):
    req_dict = get_dict(request)
    if request.method == 'POST':
        pass
    if request.method == 'GET':
        return HttpResponse("hi")
    if request.method == 'PUT':
        pass
    raise Http404


def activity_state(request):
    req_dict = get_dict(request)
    if request.method == 'PUT':
        try:
            activityId = req_dict['activityId']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but activityId parameter is missing.." % request.method)
        try:
            actor = req_dict['actor']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but actor parameter is missing.." % request.method)
        try:
            stateId = req_dict['stateId']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but stateId parameter is missing.." % request.method)
        registrationId = req_dict.get('registrationId', None)
        if registrationId:
            return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - registrationId = %s - stateId = %s" % (request.method, activityId, actor, registrationId, stateId))
        return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - stateId = %s" % (request.method, activityId, actor, stateId))

    if request.method == 'GET':
        try:
            activityId = req_dict['activityId']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but activityId parameter is missing.." % request.method)
        try:
            actor = req_dict['actor']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but actor parameter is missing.." % request.method)
        registrationId = req_dict.get('registrationId', None)
        stateId = req_dict.get('stateId', None)
        if stateId:
            if registrationId:
                return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - registrationId = %s - stateId = %s" % (request.method, activityId, actor, registrationId, stateId))
            return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - stateId = %s" % (request.method, activityId, actor, stateId))
        since = req_dict.get('since', None)
        if registrationId or since:
            if registrationId and since:
                return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - registrationId = %s - since = %s" % (request.method, activityId, actor, registrationId, since))
            elif registrationId:
                return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - registrationId = %s" % (request.method, activityId, actor, registrationId))
            else:
                return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - since = %s" % (request.method, activityId, actor, since))
        return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s" % (request.method, activityId, actor))
    
    if request.method == 'DELETE':
        try:
            activityId = req_dict['activityId']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but activityId parameter is missing.." % request.method)
        try:
            actor = req_dict['actor']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but actor parameter is missing.." % request.method)
        registrationId = req_dict.get('registrationId', None)
        stateId = req_dict.get('stateId', None)
        if stateId:
            if registrationId:
                return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - registrationId = %s - stateId = %s" % (request.method, activityId, actor, registrationId, stateId))
            return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - stateId = %s" % (request.method, activityId, actor, stateId))
        if registrationId:
            return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - registrationId = %s" % (request.method, activityId, actor, registrationId))
        return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s" % (request.method, activityId, actor))
        
    raise Http404


def activity_profile(request):
    req_dict = get_dict(request)
    if request.method == 'PUT':
        try: # not using request.GET.get('param', 'default val') cuz activityId is mandatory
            activityId = req_dict['activityId']
        except KeyError:
            return HttpResponse("Error -- activity_profile - method = %s, but activityId parameter missing.." % request.method)
        try:
            profileId = req_dict['profileId']
        except KeyError:
            return HttpResponse("Error -- activity_profile - method = %s, but profileId parameter missing.." % request.method)
        return HttpResponse("Success -- activity_profile - method = %s - activityId = %s - profileId = %s" % (request.method, activityId, profileId))
    
    if request.method == 'GET':
        try: # not using request.GET.get('param', 'default val') cuz activityId is mandatory
            activityId = req_dict['activityId']
            profileId = req_dict.get('profileId', None)
            if profileId:
                return HttpResponse("Success -- activity_profile - method = %s - activityId = %s - profileId = %s" % (request.method, activityId, profileId))
            since = req_dict.get('since', None)
            if since:
                return HttpResponse("Success -- activity_profile - method = %s - activityId = %s - since = %s" % (request.method, activityId, since))
        except KeyError:
            return HttpResponse("Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % request.method)
        return HttpResponse("Success -- activity_profile - method = %s" % request.method)
    
    if request.method == 'DELETE':
        try: # not using request.GET.get('param', 'default val') cuz activityId is mandatory
            activityId = req_dict['activityId']
        except KeyError:
            return HttpResponse("Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % request.method)
        try:
            profileId = req_dict.get('profileId', None)
        except KeyError:
            return HttpResponse("Error -- activity_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % request.method)
        return HttpResponse("Success -- activity_profile - method = %s - activityId = %s - profileId = %s" % (request.method, activityId, profileId))
    
    raise Http404


@require_GET
def activities(request):
    req_dict = get_dict(request)
    try:
        activityId = req_dict['activityId']
    except KeyError:
        return HttpResponse("Error -- activities - method = %s, but activityId parameter is missing" % request.method)
    return HttpResponse("Success -- activities - method = %s - activityId = %s" % (request.method, activityId))


#@require_http_methods(["PUT","GET","DELETE"])    
def actor_profile(request):
    #print_req_details(request)
    req_dict = get_dict(request)
    mybody = req_dict.get('body', None)
    if mybody:
        print type(mybody)
        print mybody.keys()
    #print req_dict
    if request.method == 'PUT':
        try: # not using request.GET.get('param', 'default val') cuz actor is mandatory
            actor = req_dict['actor']
        except KeyError:
            return HttpResponse("Error -- actor_profile - method = %s, but actor parameter missing.." % request.method)
        try:
            profileId = req_dict['profileId']
        except KeyError:
            return HttpResponse("Error -- actor_profile - method = %s, but profileId parameter missing.." % request.method)
        return HttpResponse("Success -- actor_profile - method = %s - actor = %s - profileId = %s" % (request.method, actor, profileId))
    
    if request.method == 'GET':
        try: 
            actor = req_dict['actor']
            profileId = req_dict.get('profileId', None)
            if profileId:
                return HttpResponse("Success -- actor_profile - method = %s - actor = %s - profileId = %s" % (request.method, actor, profileId))
            since = req_dict.get('since', None)
            if since:
                return HttpResponse("Success -- actor_profile - method = %s - actor = %s - since = %s" % (request.method, actor, since))
        except KeyError:
            return HttpResponse("Error -- actor_profile - method = %s, but actor parameter missing.. the actor parameter is required" % request.method)
        return HttpResponse("Success -- actor_profile - method = %s - actor = %s" % (request.method, actor))
    
    if request.method == 'DELETE':
        try: 
            actor = req_dict['actor']
        except KeyError:
            return HttpResponse("Error -- actor_profile - method = %s, but no actor parameter.. the actor parameter is required" % request.method)
        try:
            profileId = req_dict.get('profileId', None)
        except KeyError:
            return HttpResponse("Error -- actor_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % request.method)
        return HttpResponse("Success -- actor_profile - method = %s - actor = %s - profileId = %s" % (request.method, actor, profileId))
    
    raise Http404


# returns a 405 (Method Not Allowed) if not a GET
#@require_http_methods(["GET"]) or shortcut
@require_GET
def actors(request):
    req_dict = get_dict(request)
    try: 
        actor = req_dict['actor']
        return HttpResponse("Success -- you hit the actors url of the ADL example LRS. actor: %s" % actor)
    except KeyError:
        return HttpResponse("Error -- actors url, but no actor parameter.. the actor parameter is required")

def print_req_details(request):
    print '=====================details==============='
    print 'method: %s' % request.method
    #print 'raw %s' % request.raw_post_data
    print 'full path: %s' % request.get_full_path()
    print 'REQUEST keys %s' % request.REQUEST.keys()
    #print 'DEL keys %s' % request.DELETE.keys()
    #print 'PUT keys %s' % request.PUT.keys()
    print 'GET keys %s' % request.GET.keys()
    print 'GET: %s' % request.GET
    print 'POST keys %s' % request.POST.keys()
    print 'POST: %s' % request.POST
    try:
        body = request.body
        print 'body: %s' % body
        print 'body as qdict: %s' % QueryDict(body)
    except:
        print 'busy body' 

    print 'META: %s' % request.META
    print '==========================================='

def get_dict(request):
    if request.method == 'GET' or request.method == 'DELETE':
        return request.GET
    # puts seem to have the parameters in the body..
    if request.method == 'POST' or request.method == 'PUT':
        ret_dict = {}
        if request.GET: # looking for parameters
            ret_dict = dict(request.GET.items())
        # looking to see if this is a form.. most likely not
        if request.META['CONTENT_TYPE'] == 'multipart/form-data':
            ret_dict.update(request.POST)
        
        body = request.body
        jsn = body.replace("'", "\"")
        if request.META['CONTENT_TYPE'] == 'x-www-form-urlencoded':
            ret_dict.update(json.loads(jsn))
        else:
            ret_dict['body'] = json.loads(jsn)
        
        print ret_dict
        return ret_dict
    return {}
    
