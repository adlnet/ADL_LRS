import json
import urllib
from base64 import b64decode

from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .forms import ValidatorForm, RegisterForm, RegClientForm

from lrs.exceptions import ParamError
from lrs.models import Statement, Verb, Agent, Activity, StatementAttachment, ActivityState
from lrs.utils.StatementValidator import StatementValidator

from oauth_provider.consts import ACCEPTED, CONSUMER_STATES
from oauth_provider.models import Consumer, Token
from oauth2_provider.provider.scope import to_names
from oauth2_provider.provider.oauth2.forms import ClientForm
from oauth2_provider.provider.oauth2.models import Client, AccessToken

@csrf_protect
@require_http_methods(["GET"])
def home(request):
    context = RequestContext(request)
    stats = {}
    stats['usercnt'] = User.objects.all().count()
    stats['stmtcnt'] = Statement.objects.all().count()
    stats['verbcnt'] = Verb.objects.all().count()
    stats['agentcnt'] = Agent.objects.filter().count()
    stats['activitycnt'] = Activity.objects.filter().count()

    form = RegisterForm()
    return render_to_response('home.html', {'stats':stats, "form": form}, context_instance=context)

@csrf_protect
@require_http_methods(["POST", "GET"])
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
                validator = StatementValidator(form.cleaned_data['jsondata'])
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
@require_http_methods(["GET"])
def actexample1(request):
    return render_to_response('actexample1.json', mimetype="application/json")
@require_http_methods(["GET"])
def actexample2(request):
    return render_to_response('actexample2.json', mimetype="application/json")

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
            return HttpResponseRedirect(reverse('adl_lrs.views.home'))
        else:
            return render_to_response('register.html', {"form": form}, context_instance=context)

@login_required()
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

@transaction.commit_on_success
@login_required()
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
@login_required()
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

@login_required()
@require_http_methods(["GET"])
def my_statements(request, template="my_statements.html", page_template="my_statements_holder.html"):
    context = {'statements': Statement.objects.filter(user=request.user).order_by('-timestamp'),'page_template': page_template}
    if request.is_ajax():
        template = page_template
    return render_to_response(template, context, context_instance=RequestContext(request))

@login_required()
@require_http_methods(["GET"])
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

@login_required()
@require_http_methods(["GET"])
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
@login_required()
@require_http_methods(["GET"])
def me(request, template='me.html'):
    client_apps = Consumer.objects.filter(user=request.user)
    access_tokens = Token.objects.filter(user=request.user, token_type=Token.ACCESS, is_approved=True)
    client_apps2 = Client.objects.filter(user=request.user)
    access_tokens2 = AccessToken.objects.filter(user=request.user)
    access_token_scopes = []
    for token in access_tokens2:
        scopes = to_names(token.scope)
        access_token_scopes.append((token, scopes))

    context_dict = {
                'client_apps':client_apps,
                'access_tokens':access_tokens,
                'client_apps2': client_apps2,
                'access_tokens2':access_token_scopes
            }    
    return render_to_response(template, context_dict, context_instance=RequestContext(request))

@login_required()
@require_http_methods(["GET", "HEAD"])
def my_download_statements(request):
    stmts = Statement.objects.filter(user=request.user).order_by('-stored')
    result = "[%s]" % ",".join([stmt.object_return() for stmt in stmts])

    response = HttpResponse(result, mimetype='application/json', status=200)
    response['Content-Length'] = len(result)
    return response

@transaction.commit_on_success
@login_required()
@require_http_methods(["GET", "POST"])
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
@login_required()
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
@login_required()
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
@login_required()
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

@login_required()
@require_http_methods(["GET"])
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('adl_lrs.views.home'))
