from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.views.decorators.http import require_http_methods, require_GET
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import render_to_response
from django.template import RequestContext
from lrs.util import req_validate, req_parse, req_process, etag, retrieve_statement
from lrs import forms, models
from objects import Actor, Activity
import logging
import json
import pdb

logger = logging.getLogger(__name__)

def home(request):
    rsp = """
    <html><head></head><body><form method="POST" action="/TCAPI/statements/">
    verb: <input type="text" name="verb"/><br/>
    sparse: <input type="radio" name="sparse" value="True"/><input type="radio" name="sparse" value="False"/><br/>
    <input type="submit" value="Submit"/>
    </form>
    """
    return HttpResponse(rsp)
    #return render_to_response('home.html')

def tcexample(request):
    return render_to_response('tcexample.xml')

def tcexample2(request):
    return render_to_response('tcexample2.xml')

def tcexample3(request):
    return render_to_response('tcexample3.xml')

def tcexample4(request):
    return render_to_response('tcexample4.xml')

def register(request):
    if request.method == 'GET':
        form = forms.RegisterForm()
        return render_to_response('register.html', {"form": form})
    elif request.method == 'POST':
        form = forms.RegisterForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['username']
            pword = form.cleaned_data['password']
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(username__exact=name)
                user = authenticate(username=name, password=pword)
                if user is None:
                    return render_to_response('register.html', {"form": form, "error_message": "%s is already registered but the password was incorrect." % name})
            except User.DoesNotExist:
                user = User.objects.create_user(name, email, pword)
            return HttpResponseRedirect(reverse('lrs.views.reg_success',args=[user.id]))
        else:
            return render_to_response('register.html', {"form": form})
    else:
        return Http404

def reg_success(request, user_id):
    user = User.objects.get(id=user_id)
    return render_to_response('reg_success.html', {"info_message": "Thanks for registering %s" % user.username})

# Called when user queries GET statement endpoint and returned list is larger than server limit (10)
def statements_more(request, more_id):
    # pdb.set_trace()
    statementResult = retrieve_statement.getStatementRequest(more_id) 
    return HttpResponse(json.dumps(statementResult, indent=4),mimetype="application/json",status=200)

@require_http_methods(["PUT","GET","POST"])
def statements(request):
    try: 
        resp = handle_request(request)
    except req_validate.NotAuthorizedException as autherr:
        r = HttpResponse(autherr, status = 401)
        r['WWW-Authenticate'] = 'Basic realm="ADLLRS"'
        return r
    except req_validate.ParamConflictError as err:
        return HttpResponse(err.message, status=409)
    except req_validate.NoParamsError as err:
        return HttpResponse(err.message, status=204)
    except Exception as err:
        return HttpResponse(err.message, status=400)
    return resp
    

@require_http_methods(["PUT","POST","GET","DELETE"])
def activity_state(request):
    try: 
        resp = handle_request(request)
    except etag.MissingEtagInfo as mei:
        return HttpResponse(mei.message, status=409)
    except etag.EtagPreconditionFail as epf:
        return HttpResponse(epf.message, status=412)
    except Actor.IDNotFoundError as nf:
        return HttpResponse(nf.message, status=404)
    except req_validate.NotAuthorizedException as autherr:
        r = HttpResponse(autherr, status = 401)
        r['WWW-Authenticate'] = 'Basic realm="ADLLRS"'
        return r
    except Exception as err:
        return HttpResponse(err.message, status=400)
    return resp
    

@require_http_methods(["PUT","POST","GET","DELETE"])
def activity_profile(request):
    try: 
        resp = handle_request(request)
    except etag.MissingEtagInfo as mei:
        return HttpResponse(mei.message, status=409)
    except etag.EtagPreconditionFail as epf:
        return HttpResponse(epf.message, status=412)
    except Activity.IDNotFoundError as nf:
        return HttpResponse(nf.message, status=404)
    except req_validate.NotAuthorizedException as autherr:
        r = HttpResponse(autherr, status = 401)
        r['WWW-Authenticate'] = 'Basic realm="ADLLRS"'
        return r
    except Exception as err:
        return HttpResponse(err.message, status=400)
    return resp


@require_GET
def activities(request):
    try: 
        resp = handle_request(request)
    except req_validate.ParamError as err:
        return HttpResponse(err.message)
    except req_process.ProcessError as err:
        return HttpResponse(err.message)
    except req_validate.NotAuthorizedException as autherr:
        r = HttpResponse(autherr, status = 401)
        r['WWW-Authenticate'] = 'Basic realm="ADLLRS"'
        return r
    except Exception as err:
        return HttpResponse(err.message, status=400)
    return resp


@require_http_methods(["PUT","POST","GET","DELETE"])    
def actor_profile(request):
    try: 
        resp = handle_request(request)
    except etag.MissingEtagInfo as mei:
        return HttpResponse(mei.message, status=409)
    except etag.EtagPreconditionFail as epf:
        return HttpResponse(epf.message, status=412)
    except Actor.IDNotFoundError as nf:
        return HttpResponse(nf.message, status=404)
    except req_validate.NotAuthorizedException as autherr:
        r = HttpResponse(autherr, status = 401)
        r['WWW-Authenticate'] = 'Basic realm="ADLLRS"'
        return r
    except Exception as err:
        return HttpResponse(err.message, status=400)
    return resp

# returns a 405 (Method Not Allowed) if not a GET
#@require_http_methods(["GET"]) or shortcut
@require_GET
def actors(request):
    try: 
        resp = handle_request(request)
    except Actor.IDNotFoundError as iderr:
        return HttpResponse(iderr, status=404)
    except req_validate.NotAuthorizedException as autherr:
        r = HttpResponse(autherr, status = 401)
        r['WWW-Authenticate'] = 'Basic realm="ADLLRS"'
        return r
    except Exception as err:
        return HttpResponse(err.message, status=400)
    return resp

def handle_request(request):
    try:
        r_dict = req_parse.parse(request)
        path = request.path
        if path.endswith('/'):
            path = path.rstrip('/')
        req_dict = validators[path][r_dict['method']](r_dict)
        # Depending on if authentication is required, req_dict will either be a dict containing the request info
        # or a list with the request info dict being the first item, with the auth info being the second item
        return processors[path][req_dict['method']](req_dict)
    except:
        raise 

validators = {
    reverse(statements) : {
        "POST" : req_validate.statements_post,
        "GET" : req_validate.statements_get,
        "PUT" : req_validate.statements_put
    },
    reverse(activity_state) : {
        "PUT" : req_validate.activity_state_put,
        "GET" : req_validate.activity_state_get,
        "DELETE" : req_validate.activity_state_delete
    },
    reverse(activity_profile) : {
        "PUT" : req_validate.activity_profile_put,
        "GET" : req_validate.activity_profile_get,
        "DELETE" : req_validate.activity_profile_delete
    },
    reverse(activities) : {
        "GET" : req_validate.activities_get
    },
    reverse(actor_profile) : {
        "PUT" : req_validate.actor_profile_put,
        "GET" : req_validate.actor_profile_get,
        "DELETE" : req_validate.actor_profile_delete
    },
   reverse(actors) : {
       "GET" : req_validate.actors_get
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
    print 'upload handlers: %s' % request.upload_handlers
    print 'content disposition: %s' % request.META.get("Content-Disposition", None)
    print 'method: %s' % request.method
    print 'raw %s' % request.raw_post_data
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
    except:
        print 'busy body' 

    print 'META: %s' % request.META
    print 'META content type: %s' % request.META['CONTENT_TYPE']
    print '==========================================='

