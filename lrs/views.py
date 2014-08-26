import json
import logging
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.context_processors import csrf
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.decorators import decorator_from_middleware
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from lrs import forms, models, exceptions
from lrs.util import req_validate, req_parse, req_process, XAPIVersionHeaderMiddleware, accept_middleware, StatementValidator
from oauth_provider.consts import ACCEPTED, CONSUMER_STATES
from oauth_provider.models import Consumer, Token

# This uses the lrs logger for LRS specific information
logger = logging.getLogger(__name__)
 
@decorator_from_middleware(accept_middleware.AcceptMiddleware)
@csrf_protect
def home(request):
    context = RequestContext(request)
    context.update(csrf(request))

    stats = {}
    stats['usercnt'] = User.objects.all().count()
    stats['stmtcnt'] = models.Statement.objects.all().count()
    stats['verbcnt'] = models.Verb.objects.all().count()
    stats['agentcnt'] = models.Agent.objects.filter().count()
    stats['activitycnt'] = models.Activity.objects.filter().count()
    return render_to_response('home.html', {'stats':stats}, context_instance=context)

@decorator_from_middleware(accept_middleware.AcceptMiddleware)
@csrf_protect
def stmt_validator(request):
    context = RequestContext(request)
    context.update(csrf(request))

    if request.method == 'GET':
        form = forms.ValidatorForm()
        return render_to_response('validator.html', {"form": form}, context_instance=context)
    elif request.method == 'POST':
        form = forms.ValidatorForm(request.POST)
        if form.is_valid():
            # Initialize validator (validates incoming data structure)
            try:
                validator = StatementValidator.StatementValidator(form.cleaned_data['jsondata'])
            except SyntaxError:
                return render_to_response('validator.html', {"form": form, "error_message": "Statement is not a properly formatted dictionary"},
                context_instance=context)
            except ValueError:
                return render_to_response('validator.html', {"form": form, "error_message": "Statement is not a properly formatted dictionary"},
                context_instance=context)                
            except Exception, e:
                return render_to_response('validator.html', {"form": form, "error_message": e.message},
                context_instance=context)

            # Once know it's valid JSON, validate keys and fields
            try:
                valid = validator.validate()
            except exceptions.ParamError, e:
                return render_to_response('validator.html', {"form": form,"error_message": e.message},
                    context_instance=context)
            else:
                return render_to_response('validator.html', {"form": form,"valid_message": valid},
                    context_instance=context)
        else:
            return render_to_response('validator.html', {"form": form},
                context_instance=context)

@decorator_from_middleware(accept_middleware.AcceptMiddleware)
def about(request):
    lrs_data = { 
        "version": ["1.0.1"],
        "Extensions":{
            "xapi": {
                "statements":
                {
                    "name": "Statements",
                    "methods": ["GET", "POST", "PUT", "HEAD"],
                    "endpoint": reverse('lrs.views.statements'),
                    "description": "Endpoint to submit and retrieve XAPI statements.",
                },
                "activities":
                {
                    "name": "Activities",
                    "methods": ["GET", "HEAD"],
                    "endpoint": reverse('lrs.views.activities'),
                    "description": "Endpoint to retrieve a complete activity object.",
                },
                "activities_state":
                {
                    "name": "Activities State",
                    "methods": ["PUT","POST","GET","DELETE", "HEAD"],
                    "endpoint": reverse('lrs.views.activity_state'),
                    "description": "Stores, fetches, or deletes the document specified by the given stateId that exists in the context of the specified activity, agent, and registration (if specified).",
                },
                "activities_profile":
                {
                    "name": "Activities Profile",
                    "methods": ["PUT","POST","GET","DELETE", "HEAD"],
                    "endpoint": reverse('lrs.views.activity_profile'),
                    "description": "Saves/retrieves/deletes the specified profile document in the context of the specified activity.",
                },
                "agents":
                {
                    "name": "Agents",
                    "methods": ["GET", "HEAD"],
                    "endpoint": reverse('lrs.views.agents'),
                    "description": "Returns a special, Person object for a specified agent.",
                },
                "agents_profile":
                {
                    "name": "Agent Profile",
                    "methods": ["PUT","POST","GET","DELETE", "HEAD"],
                    "endpoint": reverse('lrs.views.agent_profile'),
                    "description": "Saves/retrieves/deletes the specified profile document in the context of the specified agent.",
                }
            },
            "lrs":{
                "user_register":
                {
                    "name": "User Registration",
                    "methods": ["POST"],
                    "endpoint": reverse('lrs.views.register'),
                    "description": "Registers a user within the LRS.",
                },
                "client_register":
                {
                    "name": "Client Registration",
                    "methods": ["POST"],
                    "endpoint": reverse('lrs.views.reg_client'),
                    "description": "Registers a client applicaton with the LRS.",
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
                },
                "authorize":
                {
                    "name": "Oauth Authorize",
                    "methods": ["GET"],
                    "endpoint": reverse('oauth_provider.views.user_authorization'),
                    "description": "Authorize a user.",
                },
                "token":
                {
                    "name": "Oauth Token",
                    "methods": ["POST"],
                    "endpoint": reverse('oauth_provider.views.access_token'),
                    "description": "Provides Oauth token to the client.",
                }
            }
        }
    }    
    return HttpResponse(json.dumps(lrs_data), mimetype="application/json", status=200)

def actexample(request):
    return render_to_response('actexample.json', mimetype="application/json")

def actexample2(request):
    return render_to_response('actexample2.json', mimetype="application/json")

def actexample3(request):
    return render_to_response('actexample3.json', mimetype="application/json")

def actexample4(request):
    return render_to_response('actexample4.json', mimetype="application/json")

@csrf_protect
@require_http_methods(["POST", "GET"])
def register(request):
    context = RequestContext(request)
    context.update(csrf(request))
    
    if request.method == 'GET':
        form = forms.RegisterForm()
        return render_to_response('register.html', {"form": form}, context_instance=context)
    elif request.method == 'POST':
        form = forms.RegisterForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['username']
            pword = form.cleaned_data['password']
            email = form.cleaned_data['email']
            
            try:
                user = User.objects.get(username__exact=name)
            except User.DoesNotExist:
                user = User.objects.create_user(name, email, pword)
            else:
                return render_to_response('register.html', {"form": form, "error_message": "User %s already exists." % name},
                    context_instance=context)                
            
            d = {"info_message": "Thanks for registering. You can now use your name [%s] and password to sign in." % user.username}
            return render_to_response('reg_success.html', d, context_instance=context)
        else:
            return render_to_response('register.html', {"form": form}, context_instance=context)

@login_required(login_url="/XAPI/accounts/login")
@require_http_methods(["POST", "GET"])
def reg_client(request):
    if request.method == 'GET':
        form = forms.RegClientForm()
        return render_to_response('regclient.html', {"form": form}, context_instance=RequestContext(request))
    elif request.method == 'POST':
        form = forms.RegClientForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            secret = form.cleaned_data['secret']

            try:
                client = Consumer.objects.get(name__exact=name)
            except Consumer.DoesNotExist:
                client = Consumer.objects.create(name=name, description=description, user=request.user,
                    status=ACCEPTED, secret=secret)
            else:
                return render_to_response('regclient.html', {"form": form, "error_message": "%s alreay exists." % name}, context_instance=RequestContext(request))         
            
            client.generate_random_codes()
            d = {"name":client.name,"app_id":client.key, "secret":client.secret, "info_message": "Your Client Credentials"}
            return render_to_response('reg_success.html', d, context_instance=RequestContext(request))
        else:
            return render_to_response('regclient.html', {"form": form}, context_instance=RequestContext(request))

@login_required(login_url="/XAPI/accounts/login")
def me(request):
    client_apps = Consumer.objects.filter(user=request.user)
    access_tokens = Token.objects.filter(user=request.user, token_type=Token.ACCESS, is_approved=True)
    return render_to_response('me.html', {'client_apps':client_apps, 'access_tokens':access_tokens},
        context_instance=RequestContext(request))

@login_required(login_url="/XAPI/accounts/login")
def my_statements(request):
    if request.method == "DELETE":
        models.Statement.objects.filter(user=request.user).delete()
        stmts = models.Statement.objects.filter(user=request.user)
        if not stmts:
            return HttpResponse(status=204)
        else:
            raise Exception("unable to delete statements")

    stmt_id = request.GET.get("stmt_id", None)
    if stmt_id:
        s = models.Statement.objects.get(statement_id=stmt_id, user=request.user)
        return HttpResponse(s.object_return(), mimetype="application/json",status=200)
    else:
        s = {}
        paginator = Paginator(models.Statement.objects.filter(user=request.user).order_by('-timestamp').values_list('id', flat=True), 
            settings.STMTS_PER_PAGE)

        page_no = request.GET.get('page', 1)
        try:
            page = paginator.page(page_no)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            page = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            page = paginator.page(paginator.num_pages)

        idlist = page.object_list
        if idlist.count() > 0:
            stmt_objs = [stmt for stmt in models.Statement.objects.filter(id__in=(idlist)).order_by('-timestamp')]
        else: 
            stmt_objs = []

        slist = []
        for stmt in stmt_objs:
            d = {}
            d['timestamp'] = stmt.timestamp.isoformat()
            d['statement_id'] = stmt.statement_id
            d['actor_name'] = stmt.actor.get_a_name()
            d['verb'] = stmt.verb.get_display()
            d['object'] = stmt.get_object().get_a_name()
            slist.append(d)

        s['stmts'] = slist
        if page.has_previous():
            s['previous'] = "%s?page=%s" % (reverse('lrs.views.my_statements'), page.previous_page_number())
        if page.has_next():
            s['next'] = "%s?page=%s" % (reverse('lrs.views.my_statements'), page.next_page_number())

        return HttpResponse(json.dumps(s), mimetype="application/json", status=200)

@login_required(login_url="/XAPI/accounts/login")
def my_app_status(request):
    try:
        name = request.GET['app_name']
        status = request.GET['status']
        new_status = [s[0] for s in CONSUMER_STATES if s[1] == status][0] #should only be 1
        client = Consumer.objects.get(name__exact=name, user=request.user)
        client.status = new_status
        client.save()
        ret = {"app_name":client.name, "status":client.get_status_display()}
        return HttpResponse(json.dumps(ret), mimetype="application/json", status=200)
    except:
        return HttpResponse(json.dumps({"error_message":"unable to fulfill request"}), mimetype="application/json", status=400)

@login_required(login_url="/XAPI/accounts/login")
@require_http_methods(["DELETE"])
def delete_token(request):
    try:
        ids = request.GET['id'].split("-")
        token_key = ids[0]
        consumer_id = ids[1]
        ts = ids[2]
        token = Token.objects.get(user=request.user,
                                         key__startswith=token_key,
                                         consumer__id=consumer_id,
                                         timestamp=ts,
                                         token_type=Token.ACCESS,
                                         is_approved=True)
        token.is_approved = False
        token.save()
        return HttpResponse("", status=204)
    except:
        return HttpResponse("Unknown token", status=400)

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

@login_required
def user_profile(request):
    return render_to_response('registration/profile.html')

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
    reverse(agent_profile).lower() : {
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
        log_exception(request.path, err)
        return HttpResponse(err.message, status=400)
    except ValidationError as ve:
        log_exception(request.path, ve)
        return HttpResponse(ve.messages[0], status=400)
    except exceptions.Unauthorized as autherr:
        log_exception(request.path, autherr)
        r = HttpResponse(autherr, status = 401)
        r['WWW-Authenticate'] = 'Basic realm="ADLLRS"'
        return r
    except exceptions.OauthBadRequest as oauth_err:
        log_exception(request.path, oauth_err)
        return HttpResponse(oauth_err.message, status=400)
    except exceptions.OauthUnauthorized as oauth_err:
        log_exception(request.path, oauth_err)
        return HttpResponse(oauth_err.message, status=401)
    except exceptions.Forbidden as forb:
        log_exception(request.path, forb)
        return HttpResponse(forb.message, status=403)
    except exceptions.NotFound as nf:
        log_exception(request.path, nf)
        return HttpResponse(nf.message, status=404)
    except exceptions.Conflict as c:
        log_exception(request.path, c)
        return HttpResponse(c.message, status=409)
    except exceptions.PreconditionFail as pf:
        log_exception(request.path, pf)
        return HttpResponse(pf.message, status=412)
    # Added BadResponse for OAuth validation
    except HttpResponseBadRequest as br:
        log_exception(request.path, br)
        return br
    except Exception as err:
        log_exception(request.path, err)
        return HttpResponse(err.message, status=500)

def log_exception(path, ex):
    logger.info("\nException while processing: %s" % path)
    logger.exception(ex)