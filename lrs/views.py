import json
import logging
import urllib
from base64 import b64decode
from datetime import datetime

from django.conf import settings
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import transaction, IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.decorators import decorator_from_middleware
from django.utils.timezone import utc
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .exceptions import BadRequest, ParamError, Unauthorized, Forbidden, NotFound, Conflict, PreconditionFail, OauthUnauthorized, OauthBadRequest
from .forms import ValidatorForm, RegisterForm, RegClientForm
from .models import Statement, Verb, Agent, Activity, StatementAttachment, ActivityState, Hook
from .util import req_validate, req_parse, req_process, XAPIVersionHeaderMiddleware, accept_middleware, StatementValidator, util

from oauth_provider.consts import ACCEPTED, CONSUMER_STATES
from oauth_provider.models import Consumer, Token
from oauth2_provider.provider.scope import to_names
from oauth2_provider.provider.oauth2.forms import ClientForm
from oauth2_provider.provider.oauth2.models import Client, AccessToken

# This uses the lrs logger for LRS specific information
logger = logging.getLogger(__name__)
LOGIN_URL = "/accounts/login"

@decorator_from_middleware(accept_middleware.AcceptMiddleware)
@csrf_protect
def home(request):
    context = RequestContext(request)

    stats = {}
    stats['usercnt'] = User.objects.all().count()
    stats['stmtcnt'] = Statement.objects.all().count()
    stats['verbcnt'] = Verb.objects.all().count()
    stats['agentcnt'] = Agent.objects.filter().count()
    stats['activitycnt'] = Activity.objects.filter().count()

    if request.method == 'GET':
        form = RegisterForm()
        return render_to_response('home.html', {'stats':stats, "form": form}, context_instance=context)

@decorator_from_middleware(accept_middleware.AcceptMiddleware)
@csrf_protect
def stmt_validator(request):
    context = RequestContext(request)
    if request.method == 'GET':
        form = ValidatorForm()
        return render_to_response('validator.html', {"form": form}, context_instance=context)
    elif request.method == 'POST':
        form = ValidatorForm(request.POST)
        # Form should always be valid - only checks if field is required and that's handled client side
        if form.is_valid():
            # Once know it's valid JSON, validate keys and fields
            try:
                validator = StatementValidator.StatementValidator(form.cleaned_data['jsondata'])
                valid = validator.validate()
            except ParamError, e:
                clean_data = form.cleaned_data['jsondata']
                return render_to_response('validator.html', {"form": form, "error_message": e.message, "clean_data":clean_data},
                    context_instance=context)
            else:
                clean_data = json.dumps(validator.data, indent=4, sort_keys=True)
                return render_to_response('validator.html', {"form": form,"valid_message": valid, "clean_data":clean_data},
                    context_instance=context)
    return render_to_response('validator.html', {"form": form}, context_instance=context)

# Hosted example activites for the tests
def actexample1(request):
    return render_to_response('actexample1.json', mimetype="application/json")

def actexample2(request):
    return render_to_response('actexample2.json', mimetype="application/json")

@decorator_from_middleware(accept_middleware.AcceptMiddleware)
def about(request):
    lrs_data = { 
        "version": settings.XAPI_VERSIONS,
        "extensions":{
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
                    "name": "OAuth1 Client Registration",
                    "methods": ["POST"],
                    "endpoint": reverse('lrs.views.reg_client'),
                    "description": "Registers an OAuth client applicaton with the LRS.",
                },
                "client_register2":
                {
                    "name": "OAuth2 Client Registration",
                    "methods": ["POST"],
                    "endpoint": reverse('lrs.views.reg_client2'),
                    "description": "Registers an OAuth2 client applicaton with the LRS.",
                }                
            },
            "oauth":
            {
                "initiate":
                {
                    "name": "Oauth Initiate",
                    "methods": ["POST"],
                    "endpoint": reverse('oauth:oauth_provider.views.request_token'),
                    "description": "Authorize a client and return temporary credentials.",
                },
                "authorize":
                {
                    "name": "Oauth Authorize",
                    "methods": ["GET"],
                    "endpoint": reverse('oauth:oauth_provider.views.user_authorization'),
                    "description": "Authorize a user for Oauth1.",
                },
                "token":
                {
                    "name": "Oauth Token",
                    "methods": ["POST"],
                    "endpoint": reverse('oauth:oauth_provider.views.access_token'),
                    "description": "Provides Oauth token to the client.",
                }
            },
            "oauth2":
            {
                "authorize":
                {
                    "name": "Oauth2 Authorize",
                    "methods": ["GET"],
                    "endpoint": reverse('oauth2:authorize'),
                    "description": "Authorize a user for Oauth2.",
                },
                "access_token":
                {
                    "name": "Oauth2 Token",
                    "methods": ["POST"],
                    "endpoint": reverse('oauth2:access_token'),
                    "description": "Provides Oauth2 token to the client.",
                }
            }            
        }
    }    
    return HttpResponse(json.dumps(lrs_data), mimetype="application/json", status=200)

@csrf_protect
@require_http_methods(["POST", "GET"])
def register(request):
    context = RequestContext(request)
    
    if request.method == 'GET':
        form = RegisterForm()
        return render_to_response('register.html', {"form": form}, context_instance=context)
    elif request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['username']
            pword = form.cleaned_data['password']
            email = form.cleaned_data['email']
            
            # If username doesn't already exist
            if not User.objects.filter(username__exact=name).count():
                # if email doesn't already exist
                if not User.objects.filter(email__exact=email).count():
                    User.objects.create_user(name, email, pword)
                else:
                    return render_to_response('register.html', {"form": form, "error_message": "Email %s is already registered." % email},
                        context_instance=context)                    
            else:
                return render_to_response('register.html', {"form": form, "error_message": "User %s already exists." % name},
                    context_instance=context)                
            
            # If a user is already logged in, log them out
            if request.user.is_authenticated():
                logout(request)

            new_user = authenticate(username=name, password=pword)
            login(request, new_user)
            return HttpResponseRedirect(reverse('lrs.views.home'))
        else:
            return render_to_response('register.html', {"form": form}, context_instance=context)

@login_required(login_url=LOGIN_URL)
@require_http_methods(["GET"])
def admin_attachments(request, path):
    if request.user.is_superuser:
        try:
            att_object = StatementAttachment.objects.get(sha2=path)
        except StatementAttachment.DoesNotExist:
            raise HttpResponseNotFound("File not found")
        chunks = []
        try:
            # Default chunk size is 64kb
            for chunk in att_object.payload.chunks():
                decoded_data = b64decode(chunk)
                chunks.append(decoded_data)
        except OSError:
            return HttpResponseNotFound("File not found")

        response = HttpResponse(chunks, content_type=str(att_object.contentType))
        response['Content-Disposition'] = 'attachment; filename="%s"' % path
        return response

@login_required(login_url=LOGIN_URL)
@require_http_methods(["POST", "GET"])
def reg_client(request):
    if request.method == 'GET':
        form = RegClientForm()
        return render_to_response('regclient.html', {"form": form}, context_instance=RequestContext(request))
    elif request.method == 'POST':
        form = RegClientForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            rsa_signature = form.cleaned_data['rsa']
            secret = form.cleaned_data['secret']

            try:
                client = Consumer.objects.get(name__exact=name)
            except Consumer.DoesNotExist:
                client = Consumer.objects.create(name=name, description=description, user=request.user,
                    status=ACCEPTED, secret=secret, rsa_signature=rsa_signature)
            else:
                return render_to_response('regclient.html', {"form": form, "error_message": "Client %s already exists." % name}, context_instance=RequestContext(request))         
            
            client.generate_random_codes()
            d = {"name":client.name,"app_id":client.key, "secret":client.secret, "rsa":client.rsa_signature, "info_message": "Your Client Credentials"}
            return render_to_response('reg_success.html', d, context_instance=RequestContext(request))
        else:
            return render_to_response('regclient.html', {"form": form}, context_instance=RequestContext(request))

@transaction.commit_on_success
@login_required(login_url=LOGIN_URL)
@require_http_methods(["POST", "GET"])
def reg_client2(request):
    if request.method == 'GET':
        form = ClientForm()
        return render_to_response('regclient2.html', {"form": form}, context_instance=RequestContext(request))
    elif request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid(): 
            client = form.save(commit=False)
            client.user = request.user
            client.save()
            d = {"name":client.name,"app_id":client.client_id, "secret":client.client_secret, "info_message": "Your Client Credentials"}
            return render_to_response('reg_success.html', d, context_instance=RequestContext(request))
        else:
            return render_to_response('regclient2.html', {"form": form}, context_instance=RequestContext(request))

@login_required(login_url=LOGIN_URL)
def my_statements(request, template="my_statements.html", page_template="my_statements_holder.html"):   
    context = {'statements': Statement.objects.filter(user=request.user).order_by('-timestamp'),'page_template': page_template}
    
    if request.is_ajax():
        template = page_template
    return render_to_response(template, context, context_instance=RequestContext(request))

@login_required(login_url=LOGIN_URL)
def my_activity_states(request, template="my_activity_states.html", page_template="my_activity_states_holder.html"):
    try:
        ag = Agent.objects.get(mbox="mailto:" + request.user.email)
    except Agent.DoesNotExist:
        ag = Agent.objects.create(mbox="mailto:" + request.user.email)
    except Agent.MultipleObjectsReturned:
        return HttpResponseBadRequest("More than one agent returned with email")

    context = {'activity_states': ActivityState.objects.filter(agent=ag).order_by('-updated', 'activity_id'), 'page_template': page_template}
    
    if request.is_ajax():
        template = page_template
    return render_to_response(template, context, context_instance=RequestContext(request))

@login_required(login_url=LOGIN_URL)
def me(request, template='me.html'):
    client_apps = Consumer.objects.filter(user=request.user)
    access_tokens = Token.objects.filter(user=request.user, token_type=Token.ACCESS, is_approved=True)
    client_apps2 = Client.objects.filter(user=request.user)
    access_tokens2 = AccessToken.objects.filter(user=request.user)
    access_token_scopes = []

    for token in access_tokens2:
        scopes = to_names(token.scope)
        access_token_scopes.append((token, scopes))

    context = {'client_apps':client_apps,
                'access_tokens':access_tokens,
                'client_apps2': client_apps2,
                'access_tokens2':access_token_scopes}

    return render_to_response(template, context, context_instance=RequestContext(request))

@login_required(login_url="/accounts/login")
@require_http_methods(["GET", "HEAD"])
def my_download_statements(request):
    stmts = Statement.objects.filter(user=request.user).order_by('-stored')
    result = "[%s]" % ",".join([stmt.object_return() for stmt in stmts])

    response = HttpResponse(result, mimetype='application/json', status=200)
    response['Content-Length'] = len(result)
    return response

@login_required(login_url=LOGIN_URL)
def my_activity_state(request):
    act_id = request.GET.get("act_id", None)
    state_id = request.GET.get("state_id", None)
    if act_id and state_id:
        try:
            ag = Agent.objects.get(mbox="mailto:" + request.user.email)
        except Agent.DoesNotExist:
            return HttpResponseNotFound("Agent does not exist")
        except Agent.MultipleObjectsReturned:
            return HttpResponseBadRequest("More than one agent returned with email")

        try:
            state = ActivityState.objects.get(activity_id=urllib.unquote(act_id), agent=ag, state_id=urllib.unquote(state_id))
        except ActivityState.DoesNotExist:
            return HttpResponseNotFound("Activity state does not exist")
        except ActivityState.MultipleObjectsReturned:
            return HttpResponseBadRequest("More than one activity state was found")
        # Really only used for the SCORM states so should only have json_state
        return HttpResponse(state.json_state, content_type=state.content_type, status=200)
    return HttpResponseBadRequest("Activity ID, State ID and are both required")

@transaction.commit_on_success
@login_required(login_url=LOGIN_URL)
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

@transaction.commit_on_success
@login_required(login_url=LOGIN_URL)
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

@transaction.commit_on_success
@login_required(login_url=LOGIN_URL)
@require_http_methods(["DELETE"])
def delete_token2(request):
    try:
        token_key = request.GET['id']
        token = AccessToken.objects.get(token=token_key)
    except:
        return HttpResponse("Unknown token", status=400)
    try:
        token.delete()
    except Exception, e:
        return HttpResponse(e.message, status=400)
    return HttpResponse("", status=204)

@transaction.commit_on_success
@login_required(login_url=LOGIN_URL)
@require_http_methods(["DELETE"])
def delete_client(request):
    try:
        client_id = request.GET['id']
        client = Client.objects.get(user=request.user,client_id=client_id)
    except:
        return HttpResponse("Unknown client", status=400)
    try:
        client.delete()
    except Exception, e:
        return HttpResponse(e.message, status=400)
    return HttpResponse("", status=204)

def logout_view(request):
    logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect(reverse('lrs.views.home'))

@require_http_methods(["DELETE"])
def my_statements_hook(request, hook_id):
    auth = None
    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META.get('HTTP_AUTHORIZATION')
    elif 'Authorization' in request.META:
        auth = request.META.get('Authorization')
    if auth:
        auth = auth.split()
        if len(auth) == 2:
            if auth[0].lower() == 'basic':
                uname, passwd = b64decode(auth[1]).split(':')
                if uname and passwd:
                    user = authenticate(username=uname, password=passwd)
                    if not user:
                        return HttpResponse("Unauthorized: Authorization failed, please verify your username and password", status=401)
                    try:
                        Hook.objects.get(hook_id=hook_id).delete()
                    except Hook.DoesNotExist:
                        return HttpResponseNotFound("The hook with ID: %s was not found" % hook_id)
                    else:
                        return HttpResponse('', status=204)  
                else:
                    return HttpResponse("Unauthorized: The format of the HTTP Basic Authorization Header value is incorrect", status=401)
            else:
                return HttpResponse("Unauthorized: HTTP Basic Authorization Header must start with Basic", status=401)
        else:
            return HttpResponse("Unauthorized: The format of the HTTP Basic Authorization Header value is incorrect", status=401)
    else:
        return HttpResponse("Unauthorized: Authorization must be supplied", status=401)

@require_http_methods(["POST"])
def my_statements_hooks(request):
    auth = None
    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META.get('HTTP_AUTHORIZATION')
    elif 'Authorization' in request.META:
        auth = request.META.get('Authorization')

    content_type = None
    if 'CONTENT_TYPE' in request.META:
        content_type = request.META.get('CONTENT_TYPE')
    elif 'Content-Type' in request.META:
        content_type = request.META.get('Content-Type')
    
    if content_type and auth:
        if 'application/json' in content_type:
            if request.body:
                try:
                    body = util.convert_to_datatype(request.body)
                except Exception:
                    return HttpResponseBadRequest("Could not parse request body")
                else:
                    auth = auth.split()
                    if len(auth) == 2:
                        if auth[0].lower() == 'basic':
                            uname, passwd = b64decode(auth[1]).split(':')
                            if uname and passwd:
                                user = authenticate(username=uname, password=passwd)
                                if not user:
                                    return HttpResponse("Unauthorized: Authorization failed, please verify your username and password", status=401)
                                try:
                                    body['user'] = user
                                    hook = Hook.objects.create(**body)
                                except IntegrityError:
                                    return HttpResponseBadRequest("Something went wrong: %s already exists" % body['name'])
                                except Exception, e:
                                    return HttpResponseBadRequest("Something went wrong: %s" % e.message)
                                else:
                                    holder = {"id": hook.hook_id}
                                    hook_location = "%s://%s%s/%s" % (settings.SITE_SCHEME, settings.SITE_DOMAIN, reverse('lrs.views.my_statements_hooks'), hook.hook_id)
                                    holder['url'] = hook_location
                                    holder['created_at'] = datetime.utcnow().replace(tzinfo=utc).isoformat()
                                    holder['updated_at'] = holder['created_at']
                                    body.pop('user')
                                    resp_data = holder.copy()
                                    resp_data.update(body)
                                    resp = HttpResponse(json.dumps(resp_data), content_type="application/json", status=201)
                                    resp['Location'] = hook_location
                                    return resp
                            else:
                                return HttpResponse("Unauthorized: The format of the HTTP Basic Authorization Header value is incorrect", status=401)
                        else:
                            return HttpResponse("Unauthorized: HTTP Basic Authorization Header must start with Basic", status=401)
                    else:
                        return HttpResponse("Unauthorized: The format of the HTTP Basic Authorization Header value is incorrect", status=401)
            else:
                return HttpResponseBadRequest("No request body found")      
        else:
            return HttpResponseBadRequest("Request's Content-Type must be 'application/json'")
    else:
        return HttpResponseBadRequest("Content-Type and Authorization both must be supplied")

# Called when user queries GET statement endpoint and returned list is larger than server limit (10)
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
@require_http_methods(["GET", "HEAD"])
def statements_more(request, more_id):
    return handle_request(request, more_id)

@require_http_methods(["PUT","GET","POST", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def statements(request):
    if request.method in ['GET', 'HEAD']:
        return doget(request)
    else:
        return doputpost(request)

def doget(request):
    return handle_request(request)   

@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def doputpost(request):
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

@transaction.commit_on_success
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

    except BadRequest as err:
        log_exception(request.path, err)
        return HttpResponse(err.message, status=400)
    except ValidationError as ve:
        log_exception(request.path, ve)
        return HttpResponse(ve.messages[0], status=400)
    except OauthBadRequest as oauth_err:
        log_exception(request.path, oauth_err)
        return HttpResponse(oauth_err.message, status=400)
    except Unauthorized as autherr:
        log_exception(request.path, autherr)
        r = HttpResponse(autherr, status = 401)
        r['WWW-Authenticate'] = 'Basic realm="ADLLRS"'
        return r
    except OauthUnauthorized as oauth_err:
        log_exception(request.path, oauth_err)
        return HttpResponse(oauth_err.message, status=401)
    except Forbidden as forb:
        log_exception(request.path, forb)
        return HttpResponse(forb.message, status=403)
    except NotFound as nf:
        log_exception(request.path, nf)
        return HttpResponse(nf.message, status=404)
    except Conflict as c:
        log_exception(request.path, c)
        return HttpResponse(c.message, status=409)
    except PreconditionFail as pf:
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
