from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.views.decorators.http import require_http_methods, require_GET
from lrs.util import req_parse, req_process

def home(request):
    rsp = """
    <html><head></head><body><form method="POST" action="/TCAPI/statements/">
    verb: <input type="text" name="verb"/><br/>
    sparse: <input type="radio" name="sparse" value="True"/><input type="radio" name="sparse" value="False"/><br/>
    <input type="submit" value="Submit"/>
    </form>
    """
    return HttpResponse(rsp)


@require_http_methods(["PUT","GET","POST"])
def statements(request):
    try: 
        resp = handle_request(request)
    except req_parse.ParamError as err:
        return HttpResponse(err.message)
    except req_process.ProcessError as err:
        return HttpResponse(err.message)
    return resp

    raise Http404


@require_http_methods(["PUT","GET","DELETE"])
def activity_state(request):
    try: 
        resp = handle_request(request)
    except req_parse.ParamError as err:
        return HttpResponse(err.message)
    except req_process.ProcessError as err:
        return HttpResponse(err.message)
    return resp
  
    raise Http404


@require_http_methods(["PUT","GET","DELETE"])
def activity_profile(request):
    try: 
        resp = handle_request(request)
    except req_parse.ParamError as err:
        return HttpResponse(err.message)
    except req_process.ProcessError as err:
        return HttpResponse(err.message)
    return resp
  
    raise Http404


@require_GET
def activities(request):
    try: 
        resp = handle_request(request)
    except req_parse.ParamError as err:
        return HttpResponse(err.message)
    except req_process.ProcessError as err:
        return HttpResponse(err.message)
    return resp


@require_http_methods(["PUT","GET","DELETE"])    
def actor_profile(request):
    try: 
        resp = handle_request(request)
    except req_parse.ParamError as err:
        return HttpResponse(err.message)
    except req_process.ProcessError as err:
        return HttpResponse(err.message)
    return resp
            
    raise Http404


# returns a 405 (Method Not Allowed) if not a GET
#@require_http_methods(["GET"]) or shortcut
@require_GET
def actors(request):
    try: 
        resp = handle_request(request)
    except Exception as err:
        return HttpResponse(err.message, status=400)
    return resp

def handle_request(request):
    try:
        req_dict = parsers[request.path][request.method](request)
        return processors[request.path][request.method](req_dict)
    except:
        raise 

parsers = {
    reverse(statements) : {
        "POST" : req_parse.statements_post,
        "GET" : req_parse.statements_get,
        "PUT" : req_parse.statements_put
    },
    reverse(activity_state) : {
        "PUT" : req_parse.activity_state_put,
        "GET" : req_parse.activity_state_get,
        "DELETE" : req_parse.activity_state_delete
    },
    reverse(activity_profile) : {
        "PUT" : req_parse.activity_profile_put,
        "GET" : req_parse.activity_profile_get,
        "DELETE" : req_parse.activity_profile_delete
    },
    reverse(activities) : {
        "GET" : req_parse.activities_get
    },
    reverse(actor_profile) : {
        "PUT" : req_parse.actor_profile_put,
        "GET" : req_parse.actor_profile_get,
        "DELETE" : req_parse.actor_profile_delete
    },
   reverse(actors) : {
       "GET" : req_parse.actors_get
   }
}

processors = {
    reverse(statements) : {
        "POST" : req_process.statements_post,
        "GET" : req_process.statements_get,
        "PUT" : req_process.statements_put
    },
    reverse(activity_state) : {
        "PUT" : req_process.activity_state_put,
        "GET" : req_process.activity_state_get,
        "DELETE" : req_process.activity_state_delete
    },
    reverse(activity_profile) : {
        "PUT" : req_process.activity_profile_put,
        "GET" : req_process.activity_profile_get,
        "DELETE" : req_process.activity_profile_delete
    },
    reverse(activities) : {
        "GET" : req_process.activities_get
    },
    reverse(actor_profile) : {
        "PUT" : req_process.actor_profile_put,
        "GET" : req_process.actor_profile_get,
        "DELETE" : req_process.actor_profile_delete
    },
   reverse(actors) : {
       "GET" : req_process.actors_get
   }
}

def print_req_details(request):
    print '=====================details==============='
    print 'method: %s' % request.method
    #print 'raw %s' % request.raw_post_data
    print 'full path: %s' % request.get_full_path()
    ##print 'REQUEST keys %s' % request.REQUEST.keys()
    #print 'DEL keys %s' % request.DELETE.keys()
    #print 'PUT keys %s' % request.PUT.keys()
    print 'GET keys %s' % request.GET.keys()
    print 'GET: %s' % request.GET
    #print 'POST keys %s' % request.POST.keys()
    #print 'POST: %s' % request.POST
    try:
        body = request.body
        print 'body: %s' % body
    except:
        print 'busy body' 

    #print 'META: %s' % request.META
    print 'META content type: %s' % request.META['CONTENT_TYPE']
    print '==========================================='
 
