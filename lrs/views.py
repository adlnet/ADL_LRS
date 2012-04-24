from django.http import HttpResponse, Http404
from django.views.decorators.http import require_http_methods, require_GET, require_POST

def home(request):
    return HttpResponse("you hit the home url of the ADL example LRS")


def statements(request):
    if request.method == 'POST':
        pass
    if request.method == 'GET':
        return HttpResponse("hi")
    if request.method == 'PUT':
        pass
    raise Http404


def activity_state(request):
    if request.method == 'PUT':
        try:
            activityId = request.PUT['activityId']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but activityId parameter is missing.." % request.method)
        try:
            actor = request.PUT['actor']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but actor parameter is missing.." % request.method)
        try:
            stateId = request.PUT['stateId']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but stateId parameter is missing.." % request.method)
        registrationId = request.PUT.get('registrationId', None)
        if registrationId:
            return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - registrationId = %s - stateId = %s" % (request.method, activityId, actor, registrationId, stateId))
        return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - stateId = %s" % (request.method, activityId, actor, stateId))

    if request.method == 'GET':
        try:
            activityId = request.GET['activityId']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but activityId parameter is missing.." % request.method)
        try:
            actor = request.GET['actor']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but actor parameter is missing.." % request.method)
        registrationId = request.GET.get('registrationId', None)
        stateId = request.GET.get('stateId', None)
        if stateId:
            if registrationId:
                return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - registrationId = %s - stateId = %s" % (request.method, activityId, actor, registrationId, stateId))
            return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - stateId = %s" % (request.method, activityId, actor, stateId))
        since = request.GET.get('since', None)
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
            activityId = request.DELETE['activityId']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but activityId parameter is missing.." % request.method)
        try:
            actor = request.DELETE['actor']
        except KeyError:
            return HttpResponse("Error -- activity_state - method = %s, but actor parameter is missing.." % request.method)
        registrationId = request.DELETE.get('registrationId', None)
        stateId = request.DELETE.get('stateId', None)
        if stateId:
            if registrationId:
                return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - registrationId = %s - stateId = %s" % (request.method, activityId, actor, registrationId, stateId))
            return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - stateId = %s" % (request.method, activityId, actor, stateId))
        if registrationId:
            return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s - registrationId = %s" % (request.method, activityId, actor, registrationId))
        return HttpResponse("Success -- activity_state - method = %s - activityId = %s - actor = %s" % (request.method, activityId, actor))
        
    raise Http404


def activity_profile(request):
    if request.method == 'PUT':
        try: # not using request.GET.get('param', 'default val') cuz activityId is mandatory
            activityId = request.PUT['activityId']
        except KeyError:
            return HttpResponse("Error -- activity_profile - method = %s, but activityId parameter missing.." % request.method)
        try:
            profileId = request.PUT['profileId']
        except KeyError:
            return HttpResponse("Error -- activity_profile - method = %s, but profileId parameter missing.." % request.method)
        return HttpResponse("Success -- activity_profile - method = %s - activityId = %s - profileId = %s" % (request.method, activityId, profileId))
    
    if request.method == 'GET':
        try: # not using request.GET.get('param', 'default val') cuz activityId is mandatory
            activityId = request.GET['activityId']
            profileId = request.GET.get('profileId', None)
            if profileId:
                return HttpResponse("Success -- activity_profile - method = %s - activityId = %s - profileId = %s" % (request.method, activityId, profileId))
            since = request.GET.get('since', None)
            if since:
                return HttpResponse("Success -- activity_profile - method = %s - activityId = %s - since = %s" % (request.method, activityId, since))
        except KeyError:
            return HttpResponse("Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % request.method)
        return HttpResponse("Success -- activity_profile - method = %s" % request.method)
    
    if request.method == 'DELETE':
        try: # not using request.GET.get('param', 'default val') cuz activityId is mandatory
            activityId = request.DELETE['activityId']
        except KeyError:
            return HttpResponse("Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % request.method)
        try:
            profileId = request.DELETE.get('profileId', None)
        except KeyError:
            return HttpResponse("Error -- activity_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % request.method)
        return HttpResponse("Success -- activity_profile - method = %s - activityId = %s - profileId = %s" % (request.method, activityId, profileId))
    
    raise Http404


@require_GET
def activities(request):
    try:
        activityId = request.GET['activityId']
    except KeyError:
        return HttpResponse("Error -- activities - method = %s, but activityId parameter is missing" % request.method)
    return HttpResponse("Success -- activities - method = %s - activityId = %s" % (request.method, activityId))


@require_http_methods(["PUT","GET","DELETE"])    
def actor_profile(request):
    if request.method == 'PUT':
        try: # not using request.GET.get('param', 'default val') cuz actor is mandatory
            actor = request.PUT['actor']
        except KeyError:
            return HttpResponse("Error -- actor_profile - method = %s, but actor parameter missing.." % request.method)
        try:
            profileId = request.PUT['profileId']
        except KeyError:
            return HttpResponse("Error -- actor_profile - method = %s, but profileId parameter missing.." % request.method)
        return HttpResponse("Success -- actor_profile - method = %s - actor = %s - profileId = %s" % (request.method, actor, profileId))
    
    if request.method == 'GET':
        try: # not using request.GET.get('param', 'default val') cuz actor is mandatory
            actor = request.GET['actor']
            profileId = request.GET.get('profileId', None)
            if profileId:
                return HttpResponse("Success -- actor_profile - method = %s - actor = %s - profileId = %s" % (request.method, actor, profileId))
            since = request.GET.get('since', None)
            if since:
                return HttpResponse("Success -- actor_profile - method = %s - actor = %s - since = %s" % (request.method, actor, since))
        except KeyError:
            return HttpResponse("Error -- actor_profile - method = %s, but no actor parameter.. the actor parameter is required" % request.method)
        return HttpResponse("Success -- actor_profile - method = %s" % request.method)
    
    if request.method == 'DELETE':
        try: # not using request.GET.get('param', 'default val') cuz actor is mandatory
            actor = request.DELETE['actor']
        except KeyError:
            return HttpResponse("Error -- actor_profile - method = %s, but no actor parameter.. the actor parameter is required" % request.method)
        try:
            profileId = request.DELETE.get('profileId', None)
        except KeyError:
            return HttpResponse("Error -- actor_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % request.method)
        return HttpResponse("Success -- actor_profile - method = %s - actor = %s - profileId = %s" % (request.method, actor, profileId))
    
    raise Http404


# returns a 405 (Method Not Allowed) if not a GET
#@require_http_methods(["GET"]) or shortcut
@require_GET
def actors(request):
    try: # not using request.GET.get('param', 'default val') cuz actor is mandatory
        actor = request.GET['actor']
        # load full actor object
        return HttpResponse("Success -- you hit the actors url of the ADL example LRS. actor: %s" % actor)
    except KeyError:
        return HttpResponse("Error -- actors url, but no actor parameter.. the actor parameter is required")
