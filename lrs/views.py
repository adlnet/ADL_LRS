import json
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.conf import settings
from django.views.decorators.http import require_http_methods, require_GET
from django.template import RequestContext
from django.contrib.auth import authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.shortcuts import render_to_response
from django.utils.decorators import decorator_from_middleware
from lrs.util import req_validate, req_parse, req_process, XAPIVersionHeaderMiddleware, accept_middleware
from lrs import forms, models, exceptions
from oauth_provider.consts import ACCEPTED, CONSUMER_STATES
import logging
import pdb
import pprint

logger = logging.getLogger(__name__)

@decorator_from_middleware(accept_middleware.AcceptMiddleware)
def home(request):
    lrs_data = { 
        "version": "1.0.0",
        "Extensions":{
            "xapi": {
                "statements":
                {
                    "name": "Statements",
                    "methods": ["GET", "POST", "PUT", "HEAD"],
                    "endpoint": reverse('lrs.views.statements'),
                    "description": "Endpoint to submit and retrieve XAPI statments.",
                    "content-types": []
                },
                "activities":
                {
                    "name": "Activities",
                    "methods": ["GET", "HEAD"],
                    "endpoint": reverse('lrs.views.activities'),
                    "description": "Endpoint to retrieve a complete activity object.",
                    "content-types": []
                },
                "activities_state":
                {
                    "name": "Activities State",
                    "methods": ["PUT","POST","GET","DELETE", "HEAD"],
                    "endpoint": reverse('lrs.views.activity_state'),
                    "description": "Stores, fetches, or deletes the document specified by the given stateId that exists in the context of the specified activity, agent, and registration (if specified).",
                    "content-types": []
                },
                "activities_profile":
                {
                    "name": "Activities Profile",
                    "methods": ["PUT","POST","GET","DELETE", "HEAD"],
                    "endpoint": reverse('lrs.views.activity_profile'),
                    "description": "Saves/retrieves/deletes the specified profile document in the context of the specified activity.",
                    "content-types": []
                },
                "agents":
                {
                    "name": "Agents",
                    "methods": ["GET", "HEAD"],
                    "endpoint": reverse('lrs.views.agents'),
                    "description": "Returns a special, Person object for a specified agent.",
                    "content-types": []
                },
                "agents_profile":
                {
                    "name": "Agent Profile",
                    "methods": ["PUT","POST","GET","DELETE", "HEAD"],
                    "endpoint": reverse('lrs.views.agent_profile'),
                    "description": "Saves/retrieves/deletes the specified profile document in the context of the specified agent.",
                    "content-types": []
                }
            },
            "lrs":{
                "user_register":
                {
                    "name": "User Registration",
                    "methods": ["POST"],
                    "endpoint": reverse('lrs.views.register'),
                    "description": "Registers a user within the LRS.",
                    "content-types": ["application/x-www-form-urlencoded"]
                },
                "client_register":
                {
                    "name": "Client Registration",
                    "methods": ["POST"],
                    "endpoint": reverse('lrs.views.reg_client'),
                    "description": "Registers a client applicaton with the LRS.",
                    "content-types": ["application/x-www-form-urlencoded"]
                }
            },
            "oauth":
            {
                "initiate":
                {
                    "name": "Oauth Initiate",
                    "methods": ["POST"],
                    "endpoint": reverse('oauth_provider.views.request_token'),
                    "description": "Authorize a client and return temporary credentials.",
                    "content-types": ["application/x-www-form-urlencoded"]
                },
                "authorize":
                {
                    "name": "Oauth Authorize",
                    "methods": ["GET"],
                    "endpoint": reverse('oauth_provider.views.user_authorization'),
                    "description": "Authorize a user.",
                    "content-types": []
                },
                "token":
                {
                    "name": "Oauth Token",
                    "methods": ["POST"],
                    "endpoint": reverse('oauth_provider.views.access_token'),
                    "description": "Provides Oauth token to the client.",
                    "content-types": ["application/x-www-form-urlencoded"]
                }
            }
        }
    }

    if "application/json" in request.accepted_types or 'about' in request.path:
        return HttpResponse(req_process.stream_response_generator(lrs_data), mimetype="application/json", status=200)
    return render_to_response('home.html', {"lrs_data": lrs_data}, context_instance=RequestContext(request))

def actexample(request):
    return render_to_response('actexample.json', mimetype="application/json")

def actexample2(request):
    return render_to_response('actexample2.json', mimetype="application/json")

def actexample3(request):
    return render_to_response('actexample3.json', mimetype="application/json")

def actexample4(request):
    return render_to_response('actexample4.json', mimetype="application/json")

def register(request):
    if request.method == 'GET':
        form = forms.RegisterForm()
        return render_to_response('register.html', {"form": form}, context_instance=RequestContext(request))
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
                    return render_to_response('register.html', {"form": form, "error_message": "%s's password was incorrect." % name},
                        context_instance=RequestContext(request))
            except User.DoesNotExist:
                user = User.objects.create_user(name, email, pword)
            d = {"info_message": "Thanks for registering %s" % user.username}
            return render_to_response('reg_success.html', d, context_instance=RequestContext(request))
        else:
            return render_to_response('register.html', {"form": form}, context_instance=RequestContext(request))
    else:
        return Http404


@login_required(login_url="/XAPI/accounts/login")
def reg_client(request):
    if request.method == 'GET':
        form = forms.RegClientForm()
        return render_to_response('regclient.html', {"form": form}, context_instance=RequestContext(request))
    elif request.method == 'POST':
        form = forms.RegClientForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            scopes = form.cleaned_data['scopes']
            try:
                client = models.Consumer.objects.get(name__exact=name)
            except models.Consumer.DoesNotExist:
                client = models.Consumer(name=name, description=description, user=request.user, status=ACCEPTED, default_scopes=",".join(scopes))
                client.save()
            else:
                return render_to_response('regclient.html', {"form": form, "error_message": "%s alreay exists." % name}, context_instance=RequestContext(request))         
            d = {"name":client.name,"app_id":client.key, "secret":client.secret, "info_message": "Your Client Credentials"}
            return render_to_response('reg_success.html', d, context_instance=RequestContext(request))

        else:
            return render_to_response('regclient.html', {"form": form}, context_instance=RequestContext(request))        
    else:
        return Http404

@login_required(login_url="/XAPI/accounts/login")
def me(request):
    client_apps = models.Consumer.objects.filter(user=request.user)
    access_tokens = models.Token.objects.filter(user=request.user, token_type=models.Token.ACCESS, is_approved=True)

    action_list = []
    #TODO: need to generate groups (user/clientapp) and get those actions, too
    user_type = ContentType.objects.get_for_model(request.user)
    parent_action_list = models.SystemAction.objects.filter(parent_action__isnull=True).filter(
        content_type__pk=user_type.id, object_id=request.user.id).order_by('-timestamp')

    for pa in parent_action_list:
        children = models.SystemAction.objects.filter(parent_action=pa).order_by('timestamp')
        action_tup = (pa, children)
        action_list.append(action_tup)

    return render_to_response('me.html', {'action_list':action_list, 'client_apps':client_apps, 'access_tokens':access_tokens},
        context_instance=RequestContext(request))

@login_required(login_url="/XAPI/accounts/login")
def my_statements(request):
    try:
        if request.method == "DELETE":
            models.statement.objects.filter(user=request.user).delete()
            stmts = models.statement.objects.filter(user=request.user)
            if not stmts:
                return HttpResponse(status=204)
            else:
                raise Exception("unable to delete statements")
        stmt_id = request.GET.get("stmt_id", None)
        if stmt_id:
            s = models.statement.objects.get(Q(statement_id=stmt_id), Q(user=request.user))
            return HttpResponse(json.dumps(s.object_return()),mimetype="application/json",status=200)
        else:
            s = {}
            slist = []
            for stmt in models.statement.objects.filter(user=request.user).order_by('-timestamp'):
                d = {}
                d['timestamp'] = stmt.timestamp.isoformat()
                d['statement_id'] = stmt.statement_id
                d['actor_name'] = stmt.actor.get_a_name()
                d['verb'] = stmt.verb.get_display()
                stmtobj, otype = stmt.get_object()
                d['object'] = stmtobj.get_a_name()
                slist.append(d)
            
            paginator = Paginator(slist, settings.STMTS_PER_PAGE)

            page_no = request.GET.get('page', 1)
            try:
                page = paginator.page(page_no)
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                page = paginator.page(1)
            except EmptyPage:
                # If page is out of range (e.g. 9999), deliver last page of results.
                page = paginator.page(paginator.num_pages)

            s['stmts'] = page.object_list
            if page.has_previous():
                s['previous'] = "%s?page=%s" % (reverse('lrs.views.my_statements'), page.previous_page_number())
            if page.has_next():
                s['next'] = "%s?page=%s" % (reverse('lrs.views.my_statements'), page.next_page_number())
            return HttpResponse(json.dumps(s), mimetype="application/json", status=200)
    except Exception as e:
        return HttpResponse(e, status=400)

@login_required(login_url="/XAPI/accounts/login")
def my_log(request, log_id):
    try:
        user_type = ContentType.objects.get_for_model(request.user)
        pa = models.SystemAction.objects.get(pk=log_id, content_type__pk=user_type.id)
        obj = pa.object_return()
        kids = models.SystemAction.objects.filter(parent_action=pa).order_by('timestamp')
        if kids:
            obj['actions'] = [k.object_return() for k in kids]
        return HttpResponse(json.dumps(obj), mimetype="application/json", status=200)
    except Exception as e:
        return HttpResponse(e, status=400)

@login_required(login_url="/XAPI/accounts/login")
def my_app_status(request):
    try:
        name = request.GET['app_name']
        status = request.GET['status']
        new_status = [s[0] for s in CONSUMER_STATES if s[1] == status][0] #should only be 1
        client = models.Consumer.objects.get(name__exact=name, user=request.user)
        client.status = new_status
        client.save()
        ret = {"app_name":client.name, "status":client.get_status_display()}
        return HttpResponse(json.dumps(ret), mimetype="application/json", status=200)
    except:
        return HttpResponse(json.dumps({"error_message":"unable to fulfill request"}), mimetype="application/json", status=400)

@login_required(login_url="/XAPI/accounts/login")
def delete_token(request):
    if request.method == "DELETE":
        try:
            ids = request.GET['id'].split("-")
            token_key = ids[0]
            consumer_id = ids[1]
            ts = ids[2]
            token = models.Token.objects.get(user=request.user,
                                             key__startswith=token_key,
                                             consumer__id=consumer_id,
                                             timestamp=ts,
                                             token_type=models.Token.ACCESS,
                                             is_approved=True)
            token.is_approved = False
            token.save()
            return HttpResponse("", status=204)
        except:
            return HttpResponse("Unknown token", status=400)
    return Http404("Unknown Request")


def logout_view(request):
    logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect(reverse('lrs.views.home'))

# Called when user queries GET statement endpoint and returned list is larger than server limit (10)
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
@require_http_methods(["GET", "HEAD"])
def statements_more(request, more_id):
    return handle_request(request, more_id)

@require_http_methods(["PUT","GET","POST", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def statements(request):
    return handle_request(request)   

@require_http_methods(["PUT","POST","GET","DELETE", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def activity_state(request):
    return handle_request(request)  

@require_http_methods(["PUT","POST","GET","DELETE", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def activity_profile(request):
    return handle_request(request)

@require_http_methods(["GET", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def activities(request):
    return handle_request(request)

@require_http_methods(["PUT","POST","GET","DELETE", "HEAD"])    
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def agent_profile(request):
    return handle_request(request)

# returns a 405 (Method Not Allowed) if not a GET
@require_http_methods(["GET", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def agents(request):
    return handle_request(request)

# THIS VIEW IS BEING USED
def oauth_authorize(request, request_token, callback_url, params):
    rsp = """
    <html><head></head><body><h1>Oauth Authorize</h1><h2>%s</h2></body></html>""" % params
    return HttpResponse(rsp)    

@login_required
def user_profile(request):
    return render_to_response('registration/profile.html')

def handle_request(request, more_id=None):
    try:
        r_dict = req_parse.parse(request, more_id)
        path = request.path.lower()
        
        if path.endswith('/'):
            path = path.rstrip('/')

        # Cutoff more_id
        if '/xapi/statements/more' in path:
            path = '/xapi/statements/more'

        req_dict = validators[path][r_dict['method']](r_dict)
        return processors[path][req_dict['method']](req_dict)

    except exceptions.BadRequest as err:
        return HttpResponse(err.message, status=400)
    except ValidationError as ve:
        return HttpResponse(ve.messages[0], status=400)
    except exceptions.Unauthorized as autherr:
        r = HttpResponse(autherr, status = 401)
        r['WWW-Authenticate'] = 'Basic realm="ADLLRS"'
        return r
    except exceptions.OauthUnauthorized as oauth_err:
        return oauth_err.response
    except exceptions.Forbidden as forb:
        return HttpResponse(forb.message, status=403)
    except exceptions.NotFound as nf:
        return HttpResponse(nf.message, status=404)
    except exceptions.Conflict as c:
        return HttpResponse(c.message, status=409)
    except exceptions.PreconditionFail as pf:
        return HttpResponse(pf.message, status=412)
    # except Exception as err:
    #     return HttpResponse(err.message, status=500)

validators = {
    reverse(statements).lower() : {
        "POST" : req_validate.statements_post,
        "GET" : req_validate.statements_get,
        "PUT" : req_validate.statements_put,
        "HEAD" : req_validate.statements_get
    },
    reverse(activity_state).lower() : {
        "POST": req_validate.activity_state_post,
        "PUT" : req_validate.activity_state_put,
        "GET" : req_validate.activity_state_get,
        "HEAD" : req_validate.activity_state_get,
        "DELETE" : req_validate.activity_state_delete
    },
    reverse(activity_profile).lower() : {
        "POST": req_validate.activity_profile_post,
        "PUT" : req_validate.activity_profile_put,
        "GET" : req_validate.activity_profile_get,
        "HEAD" : req_validate.activity_profile_get,
        "DELETE" : req_validate.activity_profile_delete
    },
    reverse(activities).lower() : {
        "GET" : req_validate.activities_get,
        "HEAD" : req_validate.activities_get
    },
    reverse(agent_profile) : {
        "POST": req_validate.agent_profile_post,
        "PUT" : req_validate.agent_profile_put,
        "GET" : req_validate.agent_profile_get,
        "HEAD" : req_validate.agent_profile_get,
        "DELETE" : req_validate.agent_profile_delete
    },
   reverse(agents).lower() : {
       "GET" : req_validate.agents_get,
       "HEAD" : req_validate.agents_get
   },
   "/xapi/statements/more" : {
        "GET" : req_validate.statements_more_get,
        "HEAD" : req_validate.statements_more_get
   }
}

processors = {
    reverse(statements).lower() : {
        "POST" : req_process.statements_post,
        "GET" : req_process.statements_get,
        "HEAD" : req_process.statements_get,
        "PUT" : req_process.statements_put
    },
    reverse(activity_state).lower() : {
        "POST": req_process.activity_state_post,
        "PUT" : req_process.activity_state_put,
        "GET" : req_process.activity_state_get,
        "HEAD" : req_process.activity_state_get,
        "DELETE" : req_process.activity_state_delete
    },
    reverse(activity_profile).lower() : {
        "POST": req_process.activity_profile_post,
        "PUT" : req_process.activity_profile_put,
        "GET" : req_process.activity_profile_get,
        "HEAD" : req_process.activity_profile_get,
        "DELETE" : req_process.activity_profile_delete
    },
    reverse(activities).lower() : {
        "GET" : req_process.activities_get,
        "HEAD" : req_process.activities_get
    },
    reverse(agent_profile).lower() : {
        "POST": req_process.agent_profile_post,
        "PUT" : req_process.agent_profile_put,
        "GET" : req_process.agent_profile_get,
        "HEAD" : req_process.agent_profile_get,
        "DELETE" : req_process.agent_profile_delete
    },
   reverse(agents).lower() : {
       "GET" : req_process.agents_get,
       "HEAD" : req_process.agents_get
   },
   "/xapi/statements/more" : {
        "GET" : req_process.statements_more_get,
        "HEAD" : req_process.statements_more_get
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

